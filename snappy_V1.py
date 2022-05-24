#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Oct 20 11:50:39 2021

@author: messi
"""
import matplotlib
from os.path import join
from glob import iglob
import pandas as pd
import numpy
import snappy
import gdal
from snappy import jpy

path = "/home/messi/02-sentinel/00-base/"
in_s1_files = sorted(list(iglob(join(path, '**', 'S1*.zip'), recursive=True)))

name, sensing_mode, product_type, polarization, height, width, band_names = ([] for i in range(7))

for i in in_s1_files:
    sensing_mode.append(i.split("_")[1])
    product_type.append(i.split("_")[2])
    polarization.append(i.split("_")[-6])
    
    s1_read = snappy.ProductIO.readProduct(i)
    name.append(s1_read.getName())
    height.append(s1_read.getSceneRasterHeight())
    width.append(s1_read.getSceneRasterWidth())
    band_names.append(s1_read.getBandNames())
    df_s1_read = pd.DataFrame({'Name': name, 'Sensing Mode': sensing_mode, 'Product Type': product_type, 'Polarization': polarization, 'Height': height, 'Width': width, 'Band names': band_names})
    #print(s1_read)
    print(df_s1_read)
    
    #Thermal Noise Removal
    
    parameters = snappy.HashMap()
    parameters.put('removeThermalNoise', True)
    thermal_noise =snappy.GPF.createProduct('ThermalNoiseRemoval', parameters, s1_read)
    
    # CALIBRATION
      
    parameters = snappy.HashMap() 
    parameters.put('outputSigmaBand', True) 
    parameters.put('sourceBands', 'Intensity_VH,Intensity_VV') 
    parameters.put('selectedPolarisations', 'VH,VV') 
    parameters.put('outputImageScaleInDb', False)
    calibrated = snappy.GPF.createProduct('Calibration', parameters, thermal_noise)
    
    #Speckle Filter
    
    parameters = snappy.HashMap()
    parameters.put('filter', 'Lee')
    parameters.put('filterSizeX', 5)
    parameters.put('filterSizeY', 5)
    speckle = snappy.GPF.createProduct('Speckle-Filter', parameters, calibrated)
    
    # TERRAIN CORRECTION
    proj = '''PROJCS["WGS 84 / UTM zone 21S",
        GEOGCS["WGS 84",
            DATUM["WGS_1984",
                SPHEROID["WGS 84",6378137,298.257223563,
                    AUTHORITY["EPSG","7030"]],
                AUTHORITY["EPSG","6326"]],
            PRIMEM["Greenwich",0,
                AUTHORITY["EPSG","8901"]],
            UNIT["degree",0.0174532925199433,
                AUTHORITY["EPSG","9122"]],
            AUTHORITY["EPSG","4326"]],
        PROJECTION["Transverse_Mercator"],
        PARAMETER["latitude_of_origin",0],
        PARAMETER["central_meridian",-57],
        PARAMETER["scale_factor",0.9996],
        PARAMETER["false_easting",500000],
        PARAMETER["false_northing",10000000],
        UNIT["metre",1,
            AUTHORITY["EPSG","9001"]],
        AXIS["Easting",EAST],
        AXIS["Northing",NORTH],
        AUTHORITY["EPSG","32721"]]'''
        
    parameters = snappy.HashMap()
    parameters.put('demName', 'SRTM 3Sec')    
    parameters.put('imgResamplingMethod', 'BILINEAR_INTERPOLATION')
    parameters.put('pixelSpacingInMeter', 10.0)
    parameters.put('mapProjection', proj)
    parameters.put('nodataValueAtSea', False)
    parameters.put('saveSelectedSourceBand', True)
    terrain_correction = snappy.GPF.createProduct('Terrain-Correction', parameters, speckle)
    
    #BAND MATH
    bands = terrain_correction.getBandNames()
    #print(list(bands))
    bandvh = terrain_correction.getBand('Sigma0_VH')
    
    BandDescriptor = snappy.jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
    #Banda VH
    targetBand1 = BandDescriptor()
    targetBand1.name = 'Sigma0_VH'
    targetBand1.type = 'float32'
    targetBand1.expression = 'if (Sigma0_VH <= 0.007) then 1 else 0'
    #Banda = '/home/messi/02-sentinel/01-agua/'+name
    
    targetBand2 = BandDescriptor()
    targetBand2.name = 'Sigma0_VV'
    targetBand2.type = 'float32'
    targetBand2.expression = 'if (Sigma0_VV <= 0.02) then 1 else 0'
    
    targetBands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 2)
    targetBands[0] = targetBand1
    targetBands[1] = targetBand2
    
    parameters = snappy.HashMap()
    parameters.put('targetBands', targetBands)
    agua = snappy.GPF.createProduct('BandMaths', parameters, terrain_correction)
    
    print(agua)
    output = '/home/messi/02-sentinel/01-agua/'+str(name)
    snappy.ProductIO.writeProduct(agua, output, 'GeoTIFF-BigTIFF')
