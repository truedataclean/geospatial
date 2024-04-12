# Required
# Caris HPD PaperChartBuilder License 
# Oracle Client
# N Drive connection for Carisbatch running.

import os
import os.path
from os.path import exists
import time
import oracledb
from shapely import geometry
from osgeo import ogr, osr, gdal
import subprocess

Save = 'C:\\Temp\\chart\\single\\'
rncSave = 'C:\\Projects\\Git\\Chart\\Rnc_shp\\'


def userinput():
    chartname = input("Enter the Chart name as NZ6825: ")
    print("processing for: ",chartname)
    return chartname

def rncfromhpd(chartname):

        connection = oracledb.connect(
        user="ID",
        password="PW",
        dsn="HOST:PORT/DB")

        cursor = connection.cursor()

        print("Successfully connected to Oracle Database")

        sql = """
        select c.CHARTVER_ID, a.rep_id, c.STRINGVAL, a.panelver_id, d.compositegeom_id,b.product_status,e.intval as panelnumber, TO_CHAR(SDO_UTIL.TO_WKTGEOMETRY(d.LLDG_geom)) as GEOM
        from panel_feature_vw a, CHART_SHEET_PANEL_VW b, CHART_ATTRIBUTES_VIEW c, hpd_spatial_representation d,panel_version_attribute e 
        where a.object_acronym = '$rncpanel' and a.rep_id=d.rep_id and a.panelver_id = b.panelver_id and b.chartver_id = c.chartver_id
        and e.panelvr_panelver_id=a.panelver_id and e.attributeclass_id=171 and c.acronym = 'CHTNUM'
        and c.STRINGVAL = :c_name"""

        cursor.execute(sql, c_name = chartname)
        out_data = cursor.fetchall()
        connection.close()    
        return out_data
    
def getrncpoly(pline):
    lstring = pline.replace('LINESTRING ', '')
    lstring = lstring.strip('(')
    lstring = lstring.strip(')')

   
    clist = []
    slist = lstring.split(",")
    for pt in slist:
        cpt = pt.strip()
        rncl = cpt.split(" ")
        if float(rncl[0]) <0:
            fixlong = float(rncl[0]) + 360
            rncl[0] = str(fixlong)

        clist += [(rncl[0],rncl[1]),]
        
    #<class 'osgeo.ogr.Geometry'>
    # ring = ogr.Geometry(ogr.wkbLinearRing)        
    # for p in clist:
    #     ring.AddPoint(float(p[0]), float(p[1]))
        
    # poly = ogr.Geometry(ogr.wkbPolygon)
    # poly.AddGeometry(ring)
        
    #<class 'shapely.geometry.polygon.Polygon'>
    poly = geometry.Polygon([[p[0], p[1]] for p in clist]) 
    return poly

def expgeotiff(sheet,ChartVN,inRas):
    filepath = inRas

    batch = "carisbatch -r ExportChartToTIFF -D 300 -e EXPORT_AREA -d 32 -C RGB(255,255,255,100)  -g -p {} hpd://ID:PW@DB/db?ChartVersionId={} {} 2> c:\\temp\\process-errors.txt".format(sheet,ChartVN,filepath) 
    print('Export GeoTIFF as: ',filepath)
    if os.path.exists(filepath):
        os.remove(filepath)
        
    exportresult = os.system(batch)
    
    return exportresult

# def rncchart(poly): #----------------clip test by geometry-----
#     db_conn = "OCI:" #gdal postgres DB connection required or extend options by bound limits, polygon supports by file only. 
#     inDsn = poly
#     inRas = r'C:\Temp\chart\single\321_NZ632_1.tif'
#     outRas = r'C:\Temp\chart\single\321_NZ632_1_c.tif'

#     # out_image, out_transform = rasterio.mask.mask(inRas, [inDsn], filled = True) # A NumPy version >=1.16.5 and <1.23.0 is required current 1.26.4
#     # show(out_image)
    
#     #geo = gpd.GeoDataFrame({'geometry': inDsn}, index=[0], crs="EPSG:4326")
#     # print(geo)
#     # clipped_raster = raster.rio.clip([inDsn])
#     # clipped_raster.rio.to_raster(outRas)
#     # out_img, out_transform = mask(dataset=data, shapes=coords, crop=True)
#     warp_opts = gdal.WarpOptions(
#     format="GTiff",
#     cutlineDSName= PG: ,
#     cutlineSQL="select ST_GeomFromText({})".format(poly),
#     cropToCutline=True,
#     )
#     gdal.Warp(outRas, inRas, options=warp_opts,)
def cleanshp(shpdir):
    polyshp =shpdir +".shp"
    psf = shpdir +".dbf"
    psp = shpdir +".prj"
    psx = shpdir +".shx"
    try:
            os.remove(polyshp)
            os.remove(psf)
            os.remove(psp)
            os.remove(psx)
    except OSError as e:
            print ("Error code:", e.code)

def rncpolytoshp(poly,polyshp, sheet):     

    # create the spatial reference system, WGS84, 4326
    srs =  osr.SpatialReference()
    srs.SetFromUserInput('WGS84')
 
    driver = ogr.GetDriverByName('Esri Shapefile')
    ds = driver.CreateDataSource(polyshp)
    layer = ds.CreateLayer('CropRegion', geom_type=ogr.wkbPolygon,srs=srs)
    layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
    defn = layer.GetLayerDefn()


    feat = ogr.Feature(defn)
    feat.SetField('id', sheet)

    geom = ogr.CreateGeometryFromWkb(poly.wkb)
    feat.SetGeometry(geom)

    layer.CreateFeature(feat)
    feat = geom = None 
    ds = layer = feat = geom = None


def clippedchart(polyshp,inRas,clippedRas,clayer):
    inshp = polyshp
    inRas = inRas
    outRas = clippedRas
    if os.path.exists(outRas):
            os.remove(outRas) 
    
    OutDS= gdal.Warp(outRas, inRas, cutlineDSName= inshp, cutlineLayer= clayer, cropToCutline=True)

    OutDS = None

def main():
    chartname = userinput()
    out_data = rncfromhpd(chartname)
    for record in out_data:
        ChartVN = str(record[0])
        ChartN = record[2]
        pline = record[7]
        sheet = str(record[6])
        
        inRas = Save + ChartVN + "_" + ChartN + "_" + sheet +".tif"
        clippedRas = Save + ChartVN + "_" + ChartN + "_" + sheet +"_c.tif"
        polyshp = Save + ChartVN +"_"+ ChartN + "_" + sheet +".shp"
        shpdir = Save + ChartVN +"_"+ ChartN + "_" + sheet
        clayer = ChartVN +"_"+ ChartN + "_" + sheet
        cfile = polyshp
        
        
        if pline is None:
                print("No RNC Panel data")
                print("RNC Panel data from N Drive")
                polyshp = rncSave + ChartN + "_" + sheet +".shp"
                clayer = ChartN + "_" + sheet
                
        else: 
                print("RNC Panel data from HPD")        
                poly = getrncpoly(pline)
                if os.path.exists(polyshp):  
                    cshp = cleanshp(shpdir)
                wait = 3
                time.sleep(wait)
                rncshp = rncpolytoshp(poly,polyshp,sheet)
        
        exportresult = expgeotiff(sheet,ChartVN,inRas)
        
        if exportresult == 0:
            print("GeoTIFF Exported")
            wait = 3
            time.sleep(wait)
            clippedchart(polyshp,inRas,clippedRas,clayer)
            time.sleep(wait)
    
        else:
            print("GeoTIFF Export Error")
        

        if os.path.exists(cfile):
            cshp = cleanshp(shpdir)


if __name__ == "__main__":
    main()
    
    
