import os
import glob
import re
import geopandas as gpd
import rasterio
from rasterstats import zonal_stats  # 用于区域统计
import numpy as np
import pandas as pd


PROVINCIAL_SHP_PATH = ".\\boundaries\\省级.shp"

TIF_FILE_DIRECTORY = ".\\regions_excluded_tiffs"

OUTPUT_YEARLY_SHP_DIRECTORY = ".\\yearly_nightlight_stats"

STATISTIC_TO_CALCULATE = "mean"
NODATA_FALLBACK = 0




def extract_year_from_filename(filename):
    matches = re.findall(r'(\d{4})', filename)
    if matches:
        return matches[-1]
    return None


def perform_zonal_statistics_yearly():
    """
    主函数，为每一年执行区域统计并将结果分别保存到新的Shapefile。
    """
    print("开始执行区域统计流程 (每年生成一个Shapefile)...")
    print(f"  省级边界Shapefile: {PROVINCIAL_SHP_PATH}")
    print(f"  年度TIF文件目录: {TIF_FILE_DIRECTORY}")
    print(f"  输出年度Shapefile的目录: {OUTPUT_YEARLY_SHP_DIRECTORY}")
    print(f"  计算的统计量: {STATISTIC_TO_CALCULATE}")

    # 1. 加载省级边界Shapefile (作为基础模板)
    try:
        gdf_provinces_base = gpd.read_file(PROVINCIAL_SHP_PATH)
        print(f"成功加载省级边界模板，共 {len(gdf_provinces_base)} 个省份/区域。")
        print(f"  省级边界原始CRS: {gdf_provinces_base.crs}")
    except Exception as e:
        print(f"错误: 加载省级边界Shapefile '{PROVINCIAL_SHP_PATH}' 失败: {e}")
        return


    # 3. 查找所有相关的TIF文件
    tif_file_pattern = os.path.join(TIF_FILE_DIRECTORY, "clipped_*.tif")
    tif_files = sorted(glob.glob(tif_file_pattern))

    tif_files_tiff = sorted(glob.glob(os.path.join(TIF_FILE_DIRECTORY, "clipped_*.tiff")))
    if tif_files_tiff:
        tif_files.extend(tif_files_tiff)
        tif_files = sorted(list(set(tif_files)))  # 去重并排序

    if not tif_files:
        print(f"错误: 在目录 '{TIF_FILE_DIRECTORY}' 中未找到匹配 '{tif_file_pattern}' 的TIF文件。")
        return
    print(f"找到 {len(tif_files)} 个年度TIF文件进行处理。")

    # 4. 遍历每个TIF文件，执行区域统计并保存为单独的Shapefile
    for tif_path in tif_files:
        print(f"\n  正在处理TIF文件: {tif_path}")
        year = extract_year_from_filename(os.path.basename(tif_path))
        if not year:
            print(f"    警告: 无法从文件名 '{os.path.basename(tif_path)}' 中提取年份，跳过此文件。")
            continue

        # 为当前年份的统计数据创建一个新的列名
        new_column_name = f"NTL_{year}_{STATISTIC_TO_CALCULATE}"
        print(f"    年份: {year}, 统计结果将存入列: {new_column_name}")

        # 为当前年份创建一个省级数据的副本，避免修改原始gdf_provinces_base
        gdf_yearly_data = gdf_provinces_base.copy()

        with rasterio.open(tif_path) as src:
            raster_crs = src.crs
            raster_affine = src.transform
            nodata_value_from_raster = src.nodata
            print(f"    栅格CRS: {raster_crs}, 栅格NoData值: {nodata_value_from_raster}")

        nodata_for_stats = nodata_value_from_raster if nodata_value_from_raster is not None else NODATA_FALLBACK
        print(f"    用于区域统计的NoData值: {nodata_for_stats}")

        gdf_provinces_for_stats = gdf_yearly_data.copy()  # 使用年度副本进行可能的重投影
        if gdf_provinces_for_stats.crs != raster_crs:
            print(
                f"    省级边界CRS ({gdf_provinces_for_stats.crs}) 与栅格CRS ({raster_crs}) 不一致，正在重投影边界数据（临时副本）...")
            gdf_provinces_for_stats = gdf_provinces_for_stats.to_crs(raster_crs)
            print(f"    边界数据已临时重投影到: {gdf_provinces_for_stats.crs}")

        stats_results = zonal_stats(
            gdf_provinces_for_stats,
            tif_path,
            stats=[STATISTIC_TO_CALCULATE],
            nodata=nodata_for_stats,
            affine=raster_affine,
            geojson_out=False
        )

        calculated_values = []
        for result_dict in stats_results:
            if result_dict is None or STATISTIC_TO_CALCULATE not in result_dict:
                calculated_values.append(np.nan)
            else:
                calculated_values.append(result_dict[STATISTIC_TO_CALCULATE])

        if len(calculated_values) == len(gdf_yearly_data):
            # 将统计结果添加到当前年份的GeoDataFrame副本中
            gdf_yearly_data[new_column_name] = calculated_values
            print(f"    已将 {len(calculated_values)} 个统计值添加到 '{new_column_name}' 列。")

            # 5. 保存当前年份的Shapefile
        output_shp_filename = f"NTL_{year}.shp"
        yearly_output_shp_path = os.path.join(OUTPUT_YEARLY_SHP_DIRECTORY, output_shp_filename)

        print(f"    正在保存当前年份的Shapefile到: {yearly_output_shp_path}")
        gdf_yearly_data.to_file(yearly_output_shp_path, driver="ESRI Shapefile", encoding="utf-8")
        print(f"    已成功保存: {yearly_output_shp_path}")
    print("\n所有年度TIF文件处理完毕。")


if __name__ == '__main__':
    perform_zonal_statistics_yearly()  # 调用修改后的函数名

    print("\n--- 脚本使用说明 ---")
    print("1. 请确保已安装必要的Python库: geopandas, rasterio, rasterstats, numpy, pandas。")
    print("2. 在脚本开头的“用户配置”部分，正确设置以下变量：")
    print("   - PROVINCIAL_SHP_PATH: 指向您的省级边界Shapefile文件。")
    print("   - TIF_FILE_DIRECTORY: 指向包含年度灯光TIF文件的文件夹。")
    print("   - OUTPUT_YEARLY_SHP_DIRECTORY: 您希望保存各个年度Shapefile的目录路径。")
    print("   - STATISTIC_TO_CALCULATE: 要计算的统计量，如 'sum', 'mean'。")
    print("   - NODATA_FALLBACK: 当TIF本身未定义NoData值时使用的备用值。")
    print("3. 确保TIF文件名中包含可被提取的四位数年份。")
    print("4. 运行脚本后，会在指定的输出目录下为每一年生成一个独立的Shapefile。")
