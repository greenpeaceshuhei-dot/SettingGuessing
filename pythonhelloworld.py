import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

# ページ設定（スマホで見やすくするためワイド表示＆タイトル設定）
st.set_page_config(page_title="パチスロ設定推測・ベイズ", layout="wide")

# --- セッション状態の初期化 ---
# ボタンを押しても数値を保持するためにsession_stateを使用
if 'total_spins' not in st.session_state:
    st.session_state.total_spins = 0
if 'hit_count' not in st.session_state:
    st.session_state.hit_count = 0

# --- サイドバー：機種スペックの設定 ---
st.sidebar.header("🎰 機種スペック設定")
st.sidebar.markdown("判別したい役（ベルやボーナス）の確率を入力してください。")

# デフォルト値（質問にあった例：設定1=1/10 ... 設定6=1/4）
# 実際は分母を入力させる方が使いやすい
probs_denom = {
    1: st.sidebar.number_input("設定1の確率分母 (1/X)", value=10.0, step=0.1),
    2: st.sidebar.number_input("設定2の確率分母 (1/X)", value=9.0, step=0.1),
    3: st.sidebar.number_input("設定3の確率分母 (1/X)", value=8.0, step=0.1),
    4: st.sidebar.number_input("設定4の確率分母 (1/X)", value=6.0, step=0.1),
    5: st.sidebar.number_input("設定5の確率分母 (1/X)", value=5.0, step=0.1),
    6: st.sidebar.number_input("設定6の確率分母 (1/X)", value=4.0, step=0.1),
}

# 確率値に変換 (1/X)
probs = {k: 1/v for k, v in probs_denom.items()}

# --- メインエリア：状況入力（事前確率の調整） ---
st.title("📊 パチスロ設定推測ツール")

st.markdown("### 1. ホール状況・環境認識 (事前確率)")
st.info("「並びイベント」や「隣の台の挙動」をここに反映させます。")

# 状況選択
environment_strength = st.select_slider(
    "自分の台が「高設定」である期待度（環境根拠）",
    options=["絶望的", "弱い", "フラット(通常)", "強い", "激アツ(並び確信)"],
    value="フラット(通常)"
)

# 状況に応じた事前確率(P配分)の重み付け定義
# [設定1, 2, 3, 4, 5, 6] の重み
priors_weight = {
    "絶望的": np.array([80, 10, 5, 3, 1, 1]),       # 低設定濃厚
    "弱い": np.array([50, 20, 15, 10, 3, 2]),       # 通常営業の弱い店
    "フラット(通常)": np.array([1, 1, 1, 1, 1, 1]), # フラットな視点（計算上の公平）
    "強い": np.array([10, 15, 20, 25, 20, 10]),     # イベント日
    "激アツ(並び確信)": np.array([1, 1, 2, 10, 30, 56]) # 4台並び濃厚などで隣が6
}

current_prior = priors_weight[environment_strength]

# --- メインエリア：データ入力（カウント） ---
st.markdown("---")
st.markdown("### 2. カウンター (尤度計算)")

# カウントボタンの配置
col1, col2 = st.columns(2)

with col1:
    # ゲーム数（試行回数）追加ボタン
    st.caption("試行回数 (回転数)")
    if st.button("回転数 +10", use_container_width=True):
        st.session_state.total_spins += 10
    if st.button("回転数 +100", use_container_width=True):
        st.session_state.total_spins += 100

with col2:
    # 当たり回数追加ボタン
    st.caption("当たり回数 (判別要素)")
    if st.button("当たり +1 🎯", type="primary", use_container_width=True):
        st.session_state.hit_count += 1
        st.session_state.total_spins += 1 # 当たりも1回転含む場合が多いので+1しておく

# 手動修正用（間違えた時用）
with st.expander("数値の手動修正・リセット"):
    st.session_state.total_spins = st.number_input("総回転数", value=st.session_state.total_spins, step=1)
    st.session_state.hit_count = st.number_input("当たり回数", value=st.session_state.hit_count, step=1)
    if st.button("リセット"):
        st.session_state.total_spins = 0
        st.session_state.hit_count = 0
        st.rerun()

# 現在値の表示
st.metric(label="現在の確率 (当たり/回転)", 
          value=f"1/{st.session_state.total_spins / st.session_state.hit_count:.1f}" if st.session_state.hit_count > 0 else "0",
          delta=f"{st.session_state.hit_count}回 / {st.session_state.total_spins}G")


# --- ベイズ推定の計算ロジック ---

# 設定1~6のリスト
settings = np.array([1, 2, 3, 4, 5, 6])
probabilities = np.array([probs[s] for s in settings])

# 尤度 (Likelihood) の計算: P^k * (1-P)^(n-k)
# 対数尤度を使わない簡易計算（回転数が数千回を超えるとunderflowする可能性があるが、簡易ツールとしてはこれでOK）
# 精度を高めるなら対数尤度(log likelihood)への変換推奨
likelihoods = (probabilities ** st.session_state.hit_count) * \
              ((1 - probabilities) ** (st.session_state.total_spins - st.session_state.hit_count))

# 事後確率の計算 (尤度 × 事前確率)
# 事前確率を正規化（念のため）
prior_normalized = current_prior / current_prior.sum()

# 分子: 尤度 × 事前確率
unnormalized_posterior = likelihoods * prior_normalized

# 分母: 全設定の合計（周辺尤度）
marginal_likelihood = unnormalized_posterior.sum()

# 0除算回避
if marginal_likelihood == 0:
    posteriors = np.ones(6) / 6 # 全て均等に戻す
else:
    posteriors = unnormalized_posterior / marginal_likelihood

# --- 結果の表示 ---
st.markdown("---")
st.markdown("### 3. 推測結果")

# データフレーム作成
df_result = pd.DataFrame({
    '設定': [f"設定{s}" for s in settings],
    '確率(%)': posteriors * 100,
    '設定値': settings
})

# 一番可能性が高い設定
max_prob_index = posteriors.argmax()
best_setting = settings[max_prob_index]
best_prob = posteriors[max_prob_index] * 100

# 結果メッセージ
if st.session_state.total_spins == 0:
    st.warning("データを入力してください")
else:
    if best_prob > 70:
        st.success(f"現在の推測: **設定{best_setting}** が濃厚です！ ({best_prob:.1f}%)")
    elif best_prob > 40:
        st.info(f"現在の推測: **設定{best_setting}** の可能性が高いです。 ({best_prob:.1f}%)")
    else:
        st.warning(f"まだ判断が難しいです。 (設定{best_setting}? {best_prob:.1f}%)")

    # グラフ描画 (Altairを使用)
    chart = alt.Chart(df_result).mark_bar().encode(
        x=alt.X('設定', sort=None),
        y=alt.Y('確率(%)', scale=alt.Scale(domain=[0, 100])),
        color=alt.condition(
            alt.datum.設定 == f"設定{best_setting}",
            alt.value('orange'),  # 一番高い設定はオレンジ
            alt.value('steelblue')   # 他は青
        ),
        tooltip=['設定', alt.Tooltip('確率(%)', format='.1f')]
    ).properties(
        height=300
    )
    
    st.altair_chart(chart, use_container_width=True)

    # 詳細テーブル
    with st.expander("詳細数値を見る"):
        st.table(df_result.set_index('設定').style.format({'確率(%)': '{:.2f}%'}))
