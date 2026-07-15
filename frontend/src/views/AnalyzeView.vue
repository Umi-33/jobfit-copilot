<template>
  <div class="page">
    <header class="page-header">
      <div>
        <p class="eyebrow">岗位评估</p>
        <h1>岗位分析</h1>
        <p class="page-description">录入用户画像与岗位信息，查看匹配度和下一步建议。</p>
      </div>
      <span class="status-label">静态骨架</span>
    </header>

    <div class="analyze-grid">
      <section class="panel form-panel" aria-labelledby="input-heading">
        <div class="section-heading">
          <h2 id="input-heading">分析输入</h2>
          <span>暂未连接 API</span>
        </div>

        <form class="analysis-form" @submit.prevent>
          <div class="field-row">
            <label>
              <span>公司名称</span>
              <input type="text" placeholder="例如：示例科技" />
            </label>
            <label>
              <span>岗位名称</span>
              <input type="text" placeholder="例如：AI 应用开发" />
            </label>
          </div>

          <label>
            <span>用户画像</span>
            <textarea rows="7" placeholder="粘贴脱敏后的用户画像文本"></textarea>
          </label>

          <label>
            <span>岗位 JD</span>
            <textarea rows="9" placeholder="粘贴岗位职责与任职要求"></textarea>
          </label>

          <button class="primary-button" type="submit" disabled>开始分析</button>
        </form>
      </section>

      <section class="panel result-panel" aria-labelledby="result-heading">
        <div class="section-heading">
          <h2 id="result-heading">分析结果</h2>
          <span>等待输入</span>
        </div>

        <div class="result-placeholder">
          <div class="score-placeholder">--</div>
          <h3>结果将在这里展示</h3>
          <p>后续接入 API 后，此区域将显示评分、风险、待确认项和行动建议。</p>
        </div>

        <div class="placeholder-groups" aria-hidden="true">
          <div><span></span><span></span></div>
          <div><span></span><span></span></div>
          <div><span></span><span></span></div>
        </div>
      </section>
    </div>
  </div>
</template>
