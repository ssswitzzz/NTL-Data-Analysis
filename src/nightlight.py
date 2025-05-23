import streamlit as st
import time
import os
import glob
import re
import geopandas as gpd
import folium
from streamlit_folium import st_folium


st.set_page_config(layout="wide")

PNG_FILE_DIRECTORY = ".\\processed_nightlights"
FILE_PATTERN = "*.png"
yearly_shp_dir=r"C:\Users\12907\Desktop\2024-2025大二下学期\NTL-Data-Analysis-a-GIS-Software-Engineering-Project\src\yearly_nightlight_stats"


def main():
            
    PROVINCE_NAME_FIELD = "省"


    st.title("中国省级年度夜间灯光强度交互式地图")

    game_html = """
    <div id="game-container" style="text-align:center; padding:20px; border:1px solid #ddd;">
        <h3>等待时点我!</h3>
        <button id="clickButton" onclick="incrementScore()">点击!</button>
        <p>分数: <span id="score">0</span></p>
    </div>
    <script>
        let score = 0;
        function incrementScore() {
            score++;
            document.getElementById('score').innerText = score;
        }
    </script>
    """
    #@st.cache_data
    def load_yearly_data(shp_path):
        gdf = gpd.read_file(shp_path)
        gdf.loc[32,'ENG_NAME']='Macao'
        return gdf
    def get_available_years_and_files(directory):
        year_data_map = {}
        search_pattern = os.path.join(directory, f"NTL_*.shp")
        for shp_file in glob.glob(search_pattern):
            filename = os.path.basename(shp_file)
            match = re.search(r'(\d{4})', filename)  # 查找文件名中的四位数字作为年份
            if match:
                year = match.group(1)
                data_column_name = f"NTL_{year}_m"
                year_data_map[year] = {"path": shp_file, "data_column": data_column_name}

        # 按年份降序排序
        sorted_years = sorted(year_data_map.keys(), reverse=True)
        return {year: year_data_map[year] for year in sorted_years if year in year_data_map}

    st.sidebar.header("地图选项 (Map Options)")

    available_year_data = get_available_years_and_files(
        yearly_shp_dir,
    )
    sorted_years_list = list(available_year_data.keys())

    selected_year = st.sidebar.selectbox("选择年份:", sorted_years_list)

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
        "选择配色方案:",
        available_color_schemes,
        index=available_color_schemes.index('YlOrRd')  # 默认选择 'YlOrRd'
    )

    st.sidebar.info(f"当前显示年份: {selected_year}")
    st.sidebar.info(f"数据文件: {os.path.basename(selected_shp_path)}")
    st.sidebar.info(f"灯光数据列: {selected_ntl_column}")
    st.sidebar.info(f"当前配色方案: {selected_color_scheme}")

    map_progress_bar = st.progress(0)
    st.components.v1.html(game_html, height=200)
    map_status_text = st.empty()
    # 加载选定年份的数据
    gdf_provinces_yearly = load_yearly_data(selected_shp_path)

    # --- 创建Folium地图 ---
    map_center = [gdf_provinces_yearly.union_all().centroid.y, gdf_provinces_yearly.union_all().centroid.x]
    m = folium.Map(location=map_center, zoom_start=4, tiles="CartoDB positron")

    data_for_map = gdf_provinces_yearly[[PROVINCE_NAME_FIELD, selected_ntl_column, 'geometry']].copy()

    map_progress_bar.progress(30)

    choropleth_layer = folium.Choropleth(
        geo_data=data_for_map.to_json(),
        name=f'灯光强度 {selected_year}',
        data=data_for_map,
        columns=[PROVINCE_NAME_FIELD, selected_ntl_column],
        key_on=f'feature.properties.{PROVINCE_NAME_FIELD}',
        fill_color=selected_color_scheme,
        fill_opacity=0.7,
        line_opacity=0.3,
        legend_name=f'{selected_year}年 夜间灯光总强度',
        highlight=True,
        bins=20
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

    map_progress_bar.progress(60)

    folium.LayerControl().add_to(m)

    st.subheader(f"{selected_year}年 中国省级夜间灯光强度分布图 (配色方案: {selected_color_scheme})")
    with st.spinner("正在生成地图..."):
        st_folium(m, width=1200, height=700, returned_objects=[])

    map_progress_bar.progress(100)
    st.balloons()


if __name__ == '__main__':
    main()
