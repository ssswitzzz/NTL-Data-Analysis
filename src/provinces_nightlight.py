import os
import glob
import re
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats
import numpy as np

# 这个程序用于生成省级灯光强度平均值的shapefile文件，目标是在已有的省级shapefile中写入夜间灯光平均值一列
shp_path = ".\\boundaries\\省级.shp"
tiff_path = ".\\regions_excluded_tiffs"
output_dir = ".\\yearly_nightlight_stats_provinces"
stats = "mean"


gdf_provinces_base = gpd.read_file(shp_path)
tif_file_pattern = os.path.join(tiff_path, "clipped_*.tif")
tif_files = sorted(glob.glob(tif_file_pattern))

if not os.path.exists(output_dir):
    os.makedirs(output_dir)



for tif_path in tif_files:
    match = re.search(r'(\d{4})', os.path.basename(tif_path))
    year=match.group(1)
    new_column_name = f"NTL_{year}_{stats}"
    gdf_yearly_data = gdf_provinces_base.copy()

    with rasterio.open(tif_path) as src:
        raster_crs = src.crs
        raster_affine = src.transform


    gdf_provinces_for_stats = gdf_yearly_data.copy()
    if gdf_provinces_for_stats.crs != raster_crs:
        gdf_provinces_for_stats = gdf_provinces_for_stats.to_crs(raster_crs)

    stats_results = zonal_stats(
        gdf_provinces_for_stats,
        tif_path,
        stats=[stats],
        nodata=-128.0,
        affine=raster_affine,
        geojson_out=False
    )

    calculated_values = []
    for result_dict in stats_results:
        if result_dict is None or stats not in result_dict:
            calculated_values.append(np.nan)
        else:
            calculated_values.append(result_dict[stats])

    if len(calculated_values) == len(gdf_yearly_data):
        gdf_yearly_data[new_column_name] = calculated_values

    output_shp_filename = f"NTL_{year}.shp"
    yearly_output_shp_path = os.path.join(output_dir, output_shp_filename)
    gdf_yearly_data.to_file(yearly_output_shp_path, driver="ESRI Shapefile", encoding="utf-8")


