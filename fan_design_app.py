import streamlit as st
import numpy as np
import pandas as pd
from datetime import datetime

st.set_page_config(page_title="外轉子軸流扇葉設計系統", layout="wide")
st.title("🌀 外轉子軸流扇葉設計與最佳化平台")
st.success("✅ 程式已成功載入！（簡化測試版）")

st.write("目前為簡化版本，先確認能否正常顯示。")
st.info("如果看到這行文字，表示基本框架已正常。")

# 簡單測試滑桿
R_tip = st.slider("葉尖半徑 R_tip (m)", 0.05, 0.5, 0.25)
st.metric("目前設定半徑", f"{R_tip:.3f} m")

st.caption("完整版本正在修正中...")