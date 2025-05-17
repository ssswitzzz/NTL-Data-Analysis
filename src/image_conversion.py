import os
import glob
import rasterio
from rasterio.plot import show as rio_show
import geopandas as gpd  # 导入geopandas用于处理矢量边界
import matplotlib.pyplot as plt
import numpy as np
import re

# 为DMSP数据（通常范围0-63）定义一个阈值
# 如果85百分位的vmax低于此值，并且实际最大值更高，则可能需要调整vmax
DMSP_VMAX_LOWER_THRESHOLD = 10.0  # 可以根据经验调整此值


def calculate_stretch_parameters(tif_path):
    """
    计算TIF文件的拉伸参数 (vmin, vmax)。
    增加了对vmax的调整逻辑，以防止因百分位数选择不当导致的过曝。

    参数:
    tif_path (str): 输入的TIF文件路径。

    返回:
    tuple: (img_data, transform, current_vmin, current_vmax, crs)
           img_data: 第一个波段的图像数据 (float32)，NoData已设为np.nan
           transform: 地理变换参数
           current_vmin: 计算得到的拉伸最小值
           current_vmax: 计算得到的拉伸最大值
           crs: 坐标参考系
    """
    with rasterio.open(tif_path) as src:
        img_data = src.read(1).astype(np.float32)  # 读取第一个波段
        nodata_val = src.nodata

        if nodata_val is not None:
            img_data[img_data == np.float32(nodata_val)] = np.nan

        valid_data = img_data[~np.isnan(img_data)]  # 获取所有非NaN的有效数据

        current_vmin, current_vmax = 0.0, 1.0  # 默认值

        if valid_data.size > 0:
            lower_percentile = 10.0
            upper_percentile = 85.0  # 当前用于计算初始vmax的百分位数

            calculated_vmin = np.nanpercentile(valid_data, lower_percentile)
            calculated_vmax_percentile = np.nanpercentile(valid_data, upper_percentile)
            actual_max_val = np.nanmax(valid_data)  # 数据的实际最大值

            current_vmin = max(0.0, calculated_vmin)
            current_vmax = calculated_vmax_percentile  # 初始vmax候选值

            # --- 核心调整逻辑 ---
            if calculated_vmax_percentile < actual_max_val and \
                    calculated_vmax_percentile < DMSP_VMAX_LOWER_THRESHOLD:
                print(
                    f"    注意: 基于{upper_percentile}百分位计算的 vmax ({calculated_vmax_percentile:.2f}) 低于阈值({DMSP_VMAX_LOWER_THRESHOLD:.2f}) 且小于实际最大值 ({actual_max_val:.2f}).")
                print(f"    将 vmax 调整为实际最大值 ({actual_max_val:.2f}) 以尝试减少过曝。")
                current_vmax = actual_max_val
            # --- 核心调整逻辑结束 ---

            if current_vmax <= current_vmin:
                if actual_max_val > current_vmin:
                    current_vmax = actual_max_val
                else:
                    current_vmax = current_vmin + 1.0

            if current_vmin == current_vmax and abs(current_vmin - 0.0) < 1e-9:
                if actual_max_val > 0:
                    current_vmax = actual_max_val
                else:
                    current_vmax = 1.0
        else:
            print(
                f"    警告: 文件 {os.path.basename(tif_path)} 没有有效的像素数据进行拉伸。vmin, vmax 将使用默认值 {current_vmin}, {current_vmax}")

        return img_data, src.transform, current_vmin, current_vmax, src.crs


def save_stretched_tif_as_png(tif_path, output_png_path, provincial_shp_path, cmap='hot', boundary_color='white',
                              boundary_linewidth=0.5):
    """
    读取TIF文件，进行亮度拉伸，叠加省级边界，并将其保存为PNG图像。
    会打印出用于拉伸的vmin, vmax以及原始数据的实际min, max。

    参数:
    tif_path (str): 输入的TIF文件路径。
    output_png_path (str): 输出的PNG文件路径。
    provincial_shp_path (str): 省级边界Shapefile的路径。
    cmap (str): matplotlib的颜色映射表名称。
    boundary_color (str): 边界线的颜色。
    boundary_linewidth (float): 边界线的宽度。
    """
    print(f"\n正在处理文件: {tif_path}")

    img_data, transform, vmin, vmax, raster_crs = calculate_stretch_parameters(tif_path)

    print(f"  用于拉伸的 vmin: {vmin:.4f}")
    print(f"  用于拉伸的 vmax: {vmax:.4f}")

    if np.all(np.isnan(img_data)):
        actual_min_data = np.nan
        actual_max_data = np.nan
        print("  图像数据中所有值均为 NaN (可能全是NoData)。")
    else:
        try:
            actual_min_data = np.nanmin(img_data)
            actual_max_data = np.nanmax(img_data)
            print(f"  图像数据实际最小值 (忽略NaN): {actual_min_data:.4f}")
            print(f"  图像数据实际最大值 (忽略NaN): {actual_max_data:.4f}")
        except ValueError:
            actual_min_data = np.nan
            actual_max_data = np.nan
            print("  警告: 尝试计算实际min/max失败，可能所有数据点都是NaN。")

    if np.isnan(vmin) or np.isnan(vmax) or vmin >= vmax:
        print(
            f"  警告: vmin ({vmin:.2f}) 或 vmax ({vmax:.2f}) 无效或vmin>=vmax，无法进行拉伸和保存PNG。跳过 {os.path.basename(tif_path)}")
        return

    fig, ax = plt.subplots(figsize=(10, 8))  # 根据需要调整图像大小

    # 1. 绘制亮度拉伸后的栅格数据
    rio_show(img_data,
             transform=transform,
             ax=ax,
             cmap=cmap,
             vmin=vmin,
             vmax=vmax)

    # 2. 叠加省级边界
    try:
        if os.path.exists(provincial_shp_path):
            print(f"  正在加载边界文件: {provincial_shp_path}")
            gdf_provinces = gpd.read_file(provincial_shp_path)

            # 确保边界的CRS与栅格的CRS一致
            if gdf_provinces.crs != raster_crs:
                print(f"    边界文件CRS ({gdf_provinces.crs}) 与栅格CRS ({raster_crs})不一致，正在重投影边界文件...")
                gdf_provinces = gdf_provinces.to_crs(raster_crs)
                print(f"    边界文件已重投影到: {gdf_provinces.crs}")

            # 在同一个ax上绘制边界
            # facecolor='none' 表示面透明，只绘制边界
            gdf_provinces.plot(ax=ax, facecolor='none', edgecolor='black', linewidth=boundary_linewidth)
            print(f"  已叠加省级边界。")
        else:
            print(f"  警告: 省级边界文件未找到: {provincial_shp_path}。将不叠加边界。")
    except Exception as e_shp:
        print(f"  错误: 处理或叠加省级边界时发生错误: {e_shp}")

    ax.set_axis_off()  # 去掉坐标轴边框和刻度
    try:
        fig.savefig(output_png_path, format='png', bbox_inches='tight', pad_inches=0, dpi=100)
        plt.close(fig)
        print(f"  已保存拉伸并叠加边界的图像到: {output_png_path}")
    except Exception as e:
        print(f"  错误: 保存PNG文件 {output_png_path} 失败: {e}")
        plt.close(fig)


if __name__ == '__main__':
    # --- 用户配置 ---
    TIF_FILE_DIRECTORY = ".\\regions_excluded_tiffs"  # 裁剪后的TIF输入目录
    OUTPUT_PNG_DIRECTORY = "./processed_nightlights"  # 拉伸后PNG的输出目录（建议新目录名）

    # !! 新增: 省级边界Shapefile的路径 !!
    # 请确保这个路径是正确的，并且该Shapefile包含了您希望显示的中国所有省级边界（包括港澳台）
    PROVINCIAL_SHP_PATH = ".\\boundaries\\省级.shp"
    # 例如: r"D:\data\gis\china_boundary\province.shp" (Windows)
    # 或: "/home/user/data/gis/china_boundary/province.shp" (Linux/MacOS)

    # --- 配置结束 ---

    if not os.path.exists(OUTPUT_PNG_DIRECTORY):
        os.makedirs(OUTPUT_PNG_DIRECTORY)
        print(f"已创建输出目录: {OUTPUT_PNG_DIRECTORY}")

    if not os.path.exists(PROVINCIAL_SHP_PATH):
        print(f"警告!!! 省级边界文件 '{PROVINCIAL_SHP_PATH}' 未找到。图像将不会叠加边界。请检查路径。")
        # 可以选择在这里退出脚本，如果边界是必须的:
        # exit()

    dmsp_like_pattern = "clipped_DMSP-like*.tif"

    print(f"正在搜索 {TIF_FILE_DIRECTORY} 中的文件...")

    search_path_dmsp_like = os.path.join(TIF_FILE_DIRECTORY, dmsp_like_pattern)
    dmsp_like_files = glob.glob(search_path_dmsp_like)
    print(f"  找到 {len(dmsp_like_files)} 个DMSP-like文件匹配 '{dmsp_like_pattern}'")

    all_dmsp_prefix_files = glob.glob(os.path.join(TIF_FILE_DIRECTORY, "clipped_DMSP*.tif"))
    dmsp_files = [f for f in all_dmsp_prefix_files if "DMSP-like" not in os.path.basename(f)]
    print(f"  找到 {len(dmsp_files)} 个（非DMSP-like的）DMSP文件")

    tif_files_paths = sorted(list(set(dmsp_like_files + dmsp_files)))

    if not tif_files_paths:
        print(f"在 '{TIF_FILE_DIRECTORY}' 中未找到匹配的TIF文件。")
    else:
        print(f"共找到 {len(tif_files_paths)} 个TIF文件进行处理。")
        for tif_path in tif_files_paths:
            filename = os.path.basename(tif_path)
            year_match = re.findall(r'(\d{4})', filename)

            if year_match:
                year = year_match[-1]
                output_png_filename = f"{year}.png"  # 文件名中加入boundary标识
            else:
                year = "UnknownYear"
                base_name_no_ext = os.path.splitext(filename)[0]
                output_png_filename = f"{base_name_no_ext}_stretched_boundary.png"
                print(f"  警告: 无法从文件名 {filename} 中提取年份，将使用默认命名。")

            output_png_path = os.path.join(OUTPUT_PNG_DIRECTORY, output_png_filename)

            # 调用函数时传入省级边界路径
            save_stretched_tif_as_png(tif_path, output_png_path, PROVINCIAL_SHP_PATH)

    print("\n所有文件处理完毕。")
