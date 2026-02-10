import streamlit as st

st.title("設定推測くん")

# ボタンでカウント
if 'bell' not in st.session_state: st.session_state.bell = 0
if st.button('ベル引いた！', use_container_width=True):
    st.session_state.bell += 1

# ここでさっきのベイズ計算ロジックを走らせる
# prob = calculate_bayesian(st.session_state.bell, ...)
prob =0.5
st.write(f"現在のベル回数: {st.session_state.bell}")
st.metric(label="設定6の可能性", value=f"{prob:.1%}")