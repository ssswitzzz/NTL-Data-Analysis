import geopandas as gpd
import rasterio
from rasterio.mask import mask
import os
import glob
import numpy as np

# 由于数据的TIFF文件有些有港澳台数据，有些没有，所以为了便于处理，在这个程序中我将所有TIFF文件的港澳台区域切割出来。
# 要做到这一点，我的思路是用省级的shp文件，使用港澳台区域的属性字段把这三个区域筛选出来，进行掩膜切割

shp_path = ".\\boundaries\\省级.shp"
tif_folder_path = "."
output_folder_path = ".\\regions_excluded_tiffs"
attribute_name = "ENG_NAME"
regions_to_exclude = ["HongKong", "Aomen", "Taiwan"]

gdf = gpd.read_file(shp_path)
gdf_filtered = gdf[~gdf[attribute_name].isin(regions_to_exclude)]

tif_files = glob.glob(os.path.join(tif_folder_path, "*.tif"))

tif_files = sorted(list(set(tif_files)))

#这里开始对TIFF文件进行切割处理
processed_files_count = 0
for tif_path in tif_files:
    with rasterio.open(tif_path) as src:
        mask_gdf = gdf_filtered.copy()  # 使用副本以防万一

        if mask_gdf.crs != src.crs:
            mask_gdf = mask_gdf.to_crs(src.crs)
        shapes = [geom for geom in mask_gdf.geometry]


        # 进行掩膜操作
        # 有些TIFF文件没有定义NoData值，所以对于这些文件，我把nodata值设为-128，和有定义NoData值的文件保持一致
        current_nodata = src.nodata
        if current_nodata is None:
            nodata_for_masking = -128.0
        else:
            nodata_for_masking = float(current_nodata)
        out_image, out_transform = mask(src, shapes, crop=True, nodata=nodata_for_masking,
                                        all_touched=False)
        out_meta = src.meta.copy()
        out_meta.update({
            "driver": "GTiff",
            "height": out_image.shape[1],
            "width": out_image.shape[2],
            "transform": out_transform,
            "nodata": nodata_for_masking
        })

        base_name = os.path.basename(tif_path)
        output_tif_path = os.path.join(output_folder_path, f"clipped_{base_name}")

        with rasterio.open(output_tif_path, "w", **out_meta) as file:
            file.write(out_image)
