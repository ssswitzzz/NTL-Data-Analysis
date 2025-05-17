import streamlit as st
import time
import os
import glob
import re
import geopandas as gpd
import folium
from streamlit_folium import st_folium

st.set_page_config(layout="wide")


# --- (假设您已经有了 load_all_image_bytes 和相关的配置) ---
PNG_FILE_DIRECTORY = ".\\processed_nightlights"
FILE_PATTERN = "*.png"
ANIMATION_SPEED_SECONDS_INTERACTIVE = 0.2  # 用于 rerun 方法
ANIMATION_SPEED_SECONDS_ONCE = 0.1  # 用于阻塞循环方法
yearly_shp_dir=r"C:\Users\12907\Desktop\2024-2025大二下学期\NTL-Data-Analysis-a-GIS-Software-Engineering-Project\src\yearly_nightlight_stats"


def load_all_image_bytes(_year_to_file_map_tuple):
    # ... (您的 load_all_image_bytes 函数实现) ...
    # 返回一个例如 {'year': image_bytes, ...} 的字典
    year_to_file_map = dict(_year_to_file_map_tuple)
    images_bytes_dict = {}
    for year, file_path in year_to_file_map.items():
        with open(file_path, 'rb') as f:
            images_bytes_dict[year] = f.read()
    return images_bytes_dict


def main():
    #st.title("夜间灯光地图")

    # ... (代码加载文件路径，创建 year_to_file_path_map 和 sorted_years) ...
    search_path = os.path.join(PNG_FILE_DIRECTORY, FILE_PATTERN)
    png_files_paths = sorted(glob.glob(search_path))
    year_to_file_path_map = {}
    for png_path in png_files_paths:
        filename = os.path.basename(png_path)
        year_match = re.match(r'(\d{4})\.png', filename)
        if year_match:
            year = year_match.group(1)
            year_to_file_path_map[year] = png_path
    sorted_years = sorted(list(year_to_file_path_map.keys()))

    year_to_file_path_map_tuple = tuple(year_to_file_path_map.items())
    all_loaded_images_bytes = load_all_image_bytes(year_to_file_path_map_tuple)



    # --- "播放完整动画（一次性）" 按钮 ---
    st.markdown("---")
    if st.button("播放完整动画（一次性，无交互）"):
        st.session_state.playing_interactive = False  # 确保交互式动画停止
        animation_placeholder_once = st.empty()
        for year in sorted_years:  # 假设我们从头播放
            img_bytes = all_loaded_images_bytes.get(year)
            if img_bytes:
                animation_placeholder_once.image(img_bytes, use_container_width=True)
                time.sleep(ANIMATION_SPEED_SECONDS_ONCE)  # 使用为一次性播放调整的速度
            # 在这个循环中，st.session_state.current_year_index 不会被更新以驱动滑动条
            
    PROVINCE_NAME_FIELD = "省"

    # 用于构建属性列名 (例如: NTL_2020_s)
    NTL_COLUMN_PREFIX = "NTL_"
    NTL_COLUMN_SUFFIX = "_s"  # 您提到的列名后缀

    # 用于查找年度Shapefile文件 (例如: NTL_2020.shp)
    FILE_SEARCH_PREFIX_FOR_YEARLY_SHP = "NTL_"
    FILE_SEARCH_SUFFIX_FOR_YEARLY_SHP = ".shp"
    # --- 配置结束 ---


    #st.title("中国省级年度夜间灯光强度交互式地图")

    @st.cache_data  # 缓存数据加载，提高性能
    def load_yearly_data(shp_path):
        """加载单个年度的Shapefile数据并进行初步处理"""
        gdf = gpd.read_file(shp_path)
        # 确保地理数据采用Web墨卡托投影 (EPSG:4326)，这是Folium/Leaflet常用的CRS
        gdf.loc[32,'ENG_NAME']='Macao'
        return gdf
    def get_available_years_and_files(directory, file_search_prefix, file_search_suffix):
        year_data_map = {}
        search_pattern = os.path.join(directory, f"{file_search_prefix}*{file_search_suffix}")
        for shp_file in glob.glob(search_pattern):
            filename = os.path.basename(shp_file)
            match = re.search(r'(\d{4})', filename)  # 查找文件名中的四位数字作为年份
            if match:
                year = match.group(1)
                data_column_name = f"{NTL_COLUMN_PREFIX}{year}{NTL_COLUMN_SUFFIX}"  # 例如: NTL_2020_s
                year_data_map[year] = {"path": shp_file, "data_column": data_column_name}

        # 按年份降序排序
        sorted_years = sorted(year_data_map.keys(), reverse=True)
        return {year: year_data_map[year] for year in sorted_years if year in year_data_map}

    # --- Streamlit UI元素 ---
    st.sidebar.header("地图选项 (Map Options)")

    available_year_data = get_available_years_and_files(
        yearly_shp_dir,
        FILE_SEARCH_PREFIX_FOR_YEARLY_SHP,
        FILE_SEARCH_SUFFIX_FOR_YEARLY_SHP
    )
    sorted_years_list = list(available_year_data.keys())
    # sorted_years_list 应该不会为空，因为上面已经有 if not available_year_data: st.stop()
    # 但如果为空，st.selectbox 会报错，所以这里的检查是多余的，但保留无害。

    selected_year = st.sidebar.selectbox("选择年份 (Select Year):", sorted_years_list)

    # 获取选中年份对应的文件路径和数据列名
    selected_year_info = available_year_data[selected_year]
    selected_shp_path = selected_year_info["path"]
    selected_ntl_column = selected_year_info["data_column"]

    # 定义可选的Brewer颜色方案
    available_color_schemes = [
        'YlOrRd', 'PuBu', 'BuPu', 'OrRd', 'RdPu', 'BuGn', 'GnBu', 'PuBuGn',
        'PuRd', 'Blues', 'Greens', 'Greys', 'Oranges', 'Purples', 'Reds',
        'YlGn', 'YlGnBu', 'YlOrBr'
    ]
    selected_color_scheme = st.sidebar.selectbox(
        "选择配色方案 (Select Color Scheme):",
        available_color_schemes,
        index=available_color_schemes.index('YlOrRd')  # 默认选择 'YlOrRd'
    )

    st.sidebar.info(f"当前显示年份: {selected_year}")
    st.sidebar.info(f"数据文件: {os.path.basename(selected_shp_path)}")
    st.sidebar.info(f"灯光数据列: {selected_ntl_column}")
    st.sidebar.info(f"当前配色方案: {selected_color_scheme}")

    # 加载选定年份的数据
    gdf_provinces_yearly = load_yearly_data(selected_shp_path)

    # --- 创建Folium地图 ---
    map_center = [gdf_provinces_yearly.union_all().centroid.y, gdf_provinces_yearly.union_all().centroid.x]
    m = folium.Map(location=map_center, zoom_start=4, tiles="CartoDB positron")

    data_for_map = gdf_provinces_yearly[[PROVINCE_NAME_FIELD, selected_ntl_column, 'geometry']].copy()

    choropleth_layer = folium.Choropleth(
        geo_data=data_for_map.to_json(),
        name=f'灯光强度 {selected_year}',
        data=data_for_map,
        columns=[PROVINCE_NAME_FIELD, selected_ntl_column],
        key_on=f'feature.properties.{PROVINCE_NAME_FIELD}',
        fill_color=selected_color_scheme,
        fill_opacity=0.7,
        line_opacity=0.3,
        legend_name=f'{selected_year}年 夜间灯光总强度 ({NTL_COLUMN_SUFFIX.strip("_") if NTL_COLUMN_SUFFIX else "value"})',
        # 更通用的图例名称
        highlight=True,
    ).add_to(m)

    folium.GeoJsonTooltip(
        fields=[PROVINCE_NAME_FIELD, selected_ntl_column],
        aliases=['省份/区域:', f'{selected_year}年灯光强度:'],
        sticky=False,
        localize=True,
        style="""
            background-color: #F0EFEF;
            border: 2px solid black;
            border-radius: 3px;
            box-shadow: 3px;
        """
    ).add_to(choropleth_layer.geojson)

    folium.LayerControl().add_to(m)

    st.subheader(f"{selected_year}年 中国省级夜间灯光强度分布图 (配色方案: {selected_color_scheme})")
    with st.spinner("正在生成地图..."):
        st_folium(m, width=1200, height=700, returned_objects=[])

    st.caption(f"数据来源: {os.path.basename(selected_shp_path)}, 使用 '{selected_ntl_column}' 列。")

if __name__ == '__main__':
    main()
