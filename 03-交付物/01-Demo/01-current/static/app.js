const $ = (selector) => document.querySelector(selector);
const $$ = (selector) => [...document.querySelectorAll(selector)];

const form = $('#research-form');
const directionSelect = $('#direction');
const questionInput = $('#question');
const zhCount = $('#zh-count');
const enCount = $('#en-count');
const submitButton = $('#submit-button');
const formError = $('#form-error');
const loadingCard = $('#loading-card');
const apiKeyInput = $('#api-key');
const configureApiButton = $('#configure-api');
const clearApiButton = $('#clear-api');
const apiState = $('#api-state');
const apiMessage = $('#api-message');
const retrievalApiKeyInput = $('#openalex-api-key');
const configureRetrievalButton = $('#configure-retrieval-api');
const clearRetrievalButton = $('#clear-retrieval-api');
const DEFAULT_DIRECTION = 'topic_ai_enabled_information_systems';
const PAGE_SIZE = 8;

const state = {
  data: null,
  currentView: 'start',
  paperFilter: 'all',
  visiblePapers: PAGE_SIZE,
  retrievalController: null,
  loadingTimer: null,
  proposalSelection: null,
  proposalConstraints: null,
  proposalPlan: null,
};

const viewTitles = {
  start: '研究起点',
  papers: '论文结果',
  gaps: '方向与空白',
  proposal: '开题与写作',
  settings: '检索设置',
};

function switchView(view) {
  if (!viewTitles[view]) return;
  state.currentView = view;
  $$('[data-view-panel]').forEach((panel) => {
    const active = panel.dataset.viewPanel === view;
    panel.hidden = !active;
    panel.classList.toggle('active', active);
  });
  $$('.nav-item[data-view], .mobile-nav [data-view]').forEach((button) => {
    const active = button.dataset.view === view;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  $('#page-title').textContent = viewTitles[view];
  document.title = `${viewTitles[view]} · 开题舱`;
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function optionFor(direction) {
  const option = document.createElement('option');
  option.value = direction.direction_id;
  option.textContent = direction.label;
  return option;
}

async function loadDirections() {
  const response = await fetch('/api/directions', { cache: 'no-store' });
  if (!response.ok) throw new Error('方向目录读取失败');
  const catalog = await response.json();
  directionSelect.innerHTML = '<option value="">请选择一个研究大方向</option>';
  const rendered = new Set();
  catalog.groups.forEach((group) => {
    const optgroup = document.createElement('optgroup');
    optgroup.label = group.label;
    group.directions.forEach((direction) => {
      if (rendered.has(direction.direction_id)) return;
      rendered.add(direction.direction_id);
      optgroup.appendChild(optionFor(direction));
    });
    if (optgroup.children.length) directionSelect.appendChild(optgroup);
  });
  directionSelect.value = DEFAULT_DIRECTION;
}

function updateRoutePreview() {
  $('#route-preview strong').textContent = questionInput.value.trim()
    ? '围绕细分研究问题定向检索'
    : '最近五年热门五方向发现';
}

function setApiState(configured, message) {
  apiState.textContent = configured ? '已启用' : '未启用';
  apiState.classList.toggle('ready', configured);
  configureApiButton.hidden = configured;
  clearApiButton.hidden = !configured;
  apiKeyInput.hidden = configured;
  apiMessage.textContent = message || (configured
    ? '当前服务进程已启用；服务重启后自动失效。'
    : '密钥不会写入项目或回显，服务重启后自动失效。');
}

async function refreshApiState() {
  const response = await fetch('/api/health', { cache: 'no-store' });
  if (!response.ok) throw new Error('无法读取服务状态');
  const health = await response.json();
  setApiState(health.synthesis_provider === 'deepseek');
  setRetrievalApiState(health.openalex_authenticated);
  $('#service-status span').textContent = '本地服务已就绪';
  $('#service-status').classList.add('ready');
}

function setRetrievalApiState(configured, message) {
  $('#retrieval-api-state').textContent = configured ? '已认证' : '匿名额度';
  $('#retrieval-api-state').classList.toggle('ready', configured);
  retrievalApiKeyInput.hidden = configured;
  configureRetrievalButton.hidden = configured;
  clearRetrievalButton.hidden = !configured;
  $('#retrieval-api-message').textContent = message || (configured
    ? '当前服务进程使用认证额度；服务重启后自动失效。'
    : '可进行少量匿名检索；61方向批量评测需要OpenAlex免费API key。');
}

async function configureRetrievalApi() {
  const apiKey = retrievalApiKeyInput.value.trim();
  retrievalApiKeyInput.value = '';
  if (!apiKey) {
    $('#retrieval-api-message').textContent = '请输入 OpenAlex API Key。';
    retrievalApiKeyInput.focus();
    return;
  }
  configureRetrievalButton.disabled = true;
  try {
    const response = await fetch('/api/configure/retrieval', {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ openalex_api_key: apiKey }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message_to_user || '配置失败');
    setRetrievalApiState(true, data.message_to_user);
  } catch (error) {
    setRetrievalApiState(false, error.message);
  } finally {
    configureRetrievalButton.disabled = false;
  }
}

async function clearRetrievalApi() {
  clearRetrievalButton.disabled = true;
  try {
    const response = await fetch('/api/configure/retrieval/clear', { method: 'POST' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message_to_user || '清除失败');
    setRetrievalApiState(false, data.message_to_user);
  } catch (error) {
    $('#retrieval-api-message').textContent = error.message;
  } finally {
    clearRetrievalButton.disabled = false;
  }
}

async function configureApi() {
  const apiKey = apiKeyInput.value.trim();
  apiKeyInput.value = '';
  if (!apiKey) {
    apiMessage.textContent = '请输入 DeepSeek API Key。';
    apiKeyInput.focus();
    return;
  }
  configureApiButton.disabled = true;
  apiMessage.textContent = '正在启用当前运行实例…';
  try {
    const response = await fetch('/api/configure/synthesis', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        api_key: apiKey,
        base_url: 'https://api.deepseek.com',
        model: 'deepseek-v4-pro',
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message_to_user || '配置失败');
    setApiState(true, data.message_to_user);
  } catch (error) {
    setApiState(false, error.message);
  } finally {
    configureApiButton.disabled = false;
  }
}

async function clearApi() {
  clearApiButton.disabled = true;
  try {
    const response = await fetch('/api/configure/synthesis/clear', { method: 'POST' });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message_to_user || '清除失败');
    setApiState(false, data.message_to_user);
  } catch (error) {
    apiMessage.textContent = error.message;
  } finally {
    clearApiButton.disabled = false;
  }
}

function setLoading(active) {
  submitButton.disabled = active;
  loadingCard.hidden = !active;
  submitButton.querySelector('span').textContent = active ? '正在检索…' : '开始检索论文';
  clearTimeout(state.loadingTimer);
  if (active) {
    $('#loading-title').textContent = '正在匹配期刊范围…';
    $('#loading-message').textContent = '先核验知识库中的方向与期刊路由，通常需要几十秒。';
    state.loadingTimer = setTimeout(() => {
      $('#loading-title').textContent = '正在逐本核验论文…';
      $('#loading-message').textContent = '外部元数据服务响应较慢，但已找到的论文会在检索完成后立即展示，无需等待综合分析。';
    }, 9000);
  }
}

function renderPipeline(stages = []) {
  const pipeline = $('#pipeline');
  pipeline.innerHTML = '';
  stages.forEach((stage) => {
    const item = document.createElement('li');
    item.className = stage.status;
    const symbol = document.createElement('span');
    symbol.textContent = stage.status === 'complete' ? '✓' : stage.status === 'blocked' ? '!' : '·';
    const label = document.createElement('strong');
    label.textContent = stage.label;
    item.append(symbol, label);
    pipeline.appendChild(item);
  });
}

function paperMeta(paper) {
  const authors = paper.authors?.length ? paper.authors.slice(0, 4).join(', ') : '作者信息缺失';
  return `${authors} · ${paper.journal || '期刊信息缺失'} · ${paper.year || '日期缺失'}`;
}

const diagnosisLabels = {
  route_missing: '方向路由缺失',
  provider_empty: '来源返回为空',
  rate_limited: '外部来源限流',
  quality_gate_too_strict: '质量闸门或候选阈值过严',
  language_coverage_gap: '语言覆盖不足',
  query_too_narrow: '查询表达过窄',
};

function visiblePaperSet() {
  const papers = state.data?.papers || [];
  return state.paperFilter === 'all'
    ? papers
    : papers.filter((paper) => paper.language === state.paperFilter);
}

function renderPaperList() {
  const paperList = $('#paper-list');
  paperList.innerHTML = '';
  const filtered = visiblePaperSet();
  filtered.slice(0, state.visiblePapers).forEach((paper, index) => {
    const item = document.createElement('article');
    item.className = 'paper-item';
    const indexLabel = document.createElement('span');
    indexLabel.className = 'paper-index';
    indexLabel.textContent = String(index + 1).padStart(2, '0');
    const body = document.createElement('div');
    const title = document.createElement(paper.url ? 'a' : 'h4');
    title.className = 'paper-title';
    title.textContent = paper.title || '题名信息缺失';
    if (paper.url) {
      title.href = paper.url;
      title.target = '_blank';
      title.rel = 'noreferrer';
    }
    const meta = document.createElement('p');
    meta.textContent = paperMeta(paper);
    const tags = document.createElement('div');
    tags.className = 'paper-tags';
    const score = paper.score?.total;
    const evidence = { fulltext: '全文证据', abstract: '摘要证据', title_only: '仅题名' }[paper.evidence_level] || paper.evidence_level;
    [
      paper.language === 'zh' ? '中文' : '英文',
      ...(paper.journal_ranking || []),
      ...(paper.providers || [paper.metadata_source || '来源未标注']),
      evidence,
      Number.isFinite(score) ? `匹配分 ${score}` : null,
    ].filter(Boolean).forEach((value) => {
      const tag = document.createElement('span');
      tag.textContent = value;
      tags.appendChild(tag);
    });
    body.append(title, meta, tags);
    item.append(indexLabel, body);
    paperList.appendChild(item);
  });
  $('#load-more').hidden = state.visiblePapers >= filtered.length;
  if (!filtered.length) {
    const empty = document.createElement('p');
    empty.className = 'inline-empty';
    empty.textContent = '当前筛选下没有论文，换一个语言范围看看。';
    paperList.appendChild(empty);
  }
}

function renderQualityAudit(data) {
  const audit = data.coverage_audit || {};
  $('#quality-counts').textContent = [
    `原始 ${audit.raw_count ?? 0}`,
    `去重 ${audit.deduplicated_count ?? 0}`,
    `硬闸门通过 ${audit.hard_gate_pass_count ?? 0}`,
    `进入精排 ${audit.eligible_count ?? 0}`,
    `边界淘汰 ${audit.boundary_count ?? 0}`,
    `人工复核 ${audit.manual_review_count ?? 0}`,
    `Trace守恒 ${audit.count_conserved ? '是' : '否'}`,
  ].join(' · ');
  const providerList = $('#provider-status-list');
  providerList.innerHTML = '';
  (data.provider_statuses || []).forEach((item) => {
    const row = document.createElement('li');
    row.textContent = `${item.provider} · ${item.status} · ${item.returned_rows ?? 0} 条${item.reason ? ` · ${item.reason}` : ''}`;
    providerList.appendChild(row);
  });
  const expansionList = $('#expansion-list');
  expansionList.innerHTML = '';
  (data.expansion_log || []).forEach((item) => {
    const row = document.createElement('li');
    row.textContent = `${item.lane_id || item.provider || '检索Lane'} · 原始 ${item.raw_count ?? item.returned_rows ?? 0} / 边界后 ${item.post_boundary_eligible_count ?? 0}${item.stop_reason ? ` · ${item.stop_reason}` : ''}`;
    expansionList.appendChild(row);
  });
  const causes = (data.zero_result_diagnosis?.causes || []).map((value) => diagnosisLabels[value] || value);
  $('#zero-diagnosis').textContent = causes.length ? `诊断：${causes.join('；')}` : '本次没有零结果诊断项。';
  $('#score-version').textContent = data.score_config_version
    ? `精排 ${data.score_config_version} · 固定70分准入阈值已移除`
    : '旧版检索结果未提供 P1 评分拆解';
}

function renderJournalAudit(data) {
  const targets = { zh: $('#queried-zh-journals'), en: $('#queried-en-journals') };
  Object.values(targets).forEach((node) => { node.innerHTML = ''; });
  ['zh', 'en'].forEach((language) => {
    const logs = (data.search_log || []).filter((item) => item.language === language);
    if (!logs.length) {
      const empty = document.createElement('span');
      empty.className = 'journal-empty';
      empty.textContent = '本次未查询';
      targets[language].appendChild(empty);
      return;
    }
    logs.forEach((item) => {
      const chip = document.createElement('span');
      chip.textContent = `${item.journal} · 收录${item.accepted_before_dedupe || 0}篇`;
      chip.title = [item.issn, ...(item.ranking_levels || [])].filter(Boolean).join(' · ');
      targets[language].appendChild(chip);
    });
  });
}

function renderDiscovery(data) {
  state.data = data;
  const retrieved = ['RETRIEVAL_COMPLETE', 'RETRIEVAL_PARTIAL'].includes(data.status_code);
  const papers = data.papers || [];
  const zhFound = papers.filter((paper) => paper.language === 'zh').length;
  const enFound = papers.filter((paper) => paper.language === 'en').length;

  $('#papers-empty').hidden = true;
  $('#paper-content').hidden = false;
  $('#result-status').textContent = data.status_code === 'RETRIEVAL_COMPLETE' ? '检索完成' : retrieved ? '部分结果' : '未取得结果';
  $('#result-status').classList.toggle('ready', retrieved);
  $('#matched-direction').textContent = data.request.research_direction;
  $('#matched-path').textContent = data.request.derived_path_label;
  $('#found-total').textContent = papers.length;
  $('#fact-zh').textContent = zhFound;
  $('#fact-en').textContent = enFound;
  $('#stop-message').textContent = data.message_to_user;
  $('#retrieval-card').classList.toggle('warning', !retrieved);
  $('#retrieval-symbol').textContent = retrieved ? '✓' : '!';
  $('#retrieval-kicker').textContent = retrieved ? 'LIVE RETRIEVAL' : 'RETRIEVAL CHECK';
  $('#retrieval-heading').textContent = retrieved ? '动态论文检索已完成' : '动态论文检索未取得结果';

  const groups = $('#matched-groups');
  groups.innerHTML = '';
  (data.local_match?.groups || []).forEach((group) => {
    const chip = document.createElement('span');
    chip.textContent = group;
    groups.appendChild(chip);
  });
  renderPipeline(data.stages);

  $('#paper-results').hidden = !papers.length;
  $('#retrieval-audit').textContent = `中文 ${zhFound} 篇 · 英文 ${enFound} 篇 · 外部请求 ${data.search_log?.length || 0} 次`;
  $('#result-footnote').textContent = papers.length
    ? '论文已通过完整性闸门、方向边界与来源分层；研究空白仍需在选择后获取全文复核。'
    : '没有获得可核验论文时，系统不会生成模拟论文、研究方向或空白。';
  renderJournalAudit(data);
  renderQualityAudit(data);
  renderPaperList();

  const badge = $('#paper-nav-count');
  badge.textContent = papers.length;
  badge.hidden = !papers.length;
  switchView('papers');
}

function evidenceLink(paper) {
  const node = document.createElement(paper.doi ? 'a' : 'span');
  node.textContent = paper.title || paper.paper_id || '证据论文';
  if (paper.doi) {
    node.href = `https://doi.org/${paper.doi}`;
    node.target = '_blank';
    node.rel = 'noreferrer';
  }
  return node;
}

function setSynthesisNotice(message, ready = false, error = false) {
  const notice = $('#synthesis-notice');
  notice.classList.toggle('ready', ready);
  notice.classList.toggle('error', error);
  notice.innerHTML = '';
  if (!ready && !error) {
    const loader = document.createElement('span');
    loader.className = 'mini-loader';
    loader.setAttribute('aria-hidden', 'true');
    notice.appendChild(loader);
  }
  const text = document.createElement('p');
  text.textContent = message;
  notice.appendChild(text);
}

function renderSynthesis(data) {
  $('#gaps-empty').hidden = true;
  $('#synthesis-results').hidden = false;
  const list = $('#subdirection-list');
  const limitations = $('#synthesis-limitations');
  const selected = $('#selected-gap');
  list.innerHTML = '';
  limitations.innerHTML = '';
  selected.hidden = true;
  const ready = ['SYNTHESIS_COMPLETE', 'SYNTHESIS_PARTIAL'].includes(data.synthesis_status);
  setSynthesisNotice(data.synthesis_message || '尚未得到可用综合结果。', ready, !ready && data.synthesis_status !== 'SYNTHESIS_QUEUED');
  const audit = data.synthesis_audit || {};
  $('#synthesis-audit').textContent = audit.input_paper_count
    ? `输入 ${audit.input_paper_count} 篇 · 归类 ${audit.assigned_paper_count || 0} 篇`
    : ready ? '综合完成' : '综合处理中';
  $('#synthesis-audit').classList.toggle('ready', ready);

  (data.top_subdirections || []).forEach((direction, index) => {
    const card = document.createElement('article');
    card.className = 'subdirection-card';
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'subdirection-toggle';
    toggle.setAttribute('aria-expanded', index === 0 ? 'true' : 'false');
    const rank = document.createElement('span');
    rank.className = 'direction-rank';
    rank.textContent = String(index + 1).padStart(2, '0');
    const title = document.createElement('span');
    title.className = 'direction-title';
    const strong = document.createElement('strong');
    strong.textContent = direction.name_zh;
    const english = document.createElement('small');
    english.textContent = `${direction.name_en || ''} · ${direction.paper_count || 0} 篇`;
    title.append(strong, english);
    const arrow = document.createElement('span');
    arrow.className = 'direction-arrow';
    arrow.textContent = '⌄';
    toggle.append(rank, title, arrow);

    const body = document.createElement('div');
    body.className = 'subdirection-body';
    body.hidden = index !== 0;
    const description = document.createElement('p');
    description.className = 'subdirection-description';
    description.textContent = direction.description || '边界描述待全文复核。';
    body.appendChild(description);

    const gaps = (data.gap_candidates || []).filter((gap) => gap.subdirection_id === direction.subdirection_id);
    gaps.forEach((gap) => {
      const gapCard = document.createElement('div');
      gapCard.className = 'gap-card';
      const label = document.createElement('span');
      label.className = 'gap-type';
      label.textContent = `${gap.gap_type || '研究空白'} · 待全文验证`;
      const statement = document.createElement('h4');
      statement.textContent = gap.gap_statement;
      const why = document.createElement('p');
      why.textContent = gap.why_it_matters;
      const evidence = document.createElement('div');
      evidence.className = 'gap-evidence';
      const evidenceTitle = document.createElement('strong');
      evidenceTitle.textContent = '证据锚点';
      evidence.appendChild(evidenceTitle);
      (gap.evidence_papers || []).forEach((paper) => evidence.appendChild(evidenceLink(paper)));
      const innovations = document.createElement('fieldset');
      innovations.className = 'innovation-options';
      const innovationLegend = document.createElement('legend');
      innovationLegend.textContent = '再选择一个创新点';
      innovations.appendChild(innovationLegend);
      const choose = document.createElement('button');
      choose.type = 'button';
      choose.className = 'primary-button choose-gap';
      choose.textContent = '选择空白与创新点，生成开题';
      choose.disabled = true;
      let selectedInnovationId = '';
      let selectedInnovationText = '';
      (gap.innovation_candidates || []).forEach((value, innovationIndex) => {
        const innovationId = `${gap.gap_id}_innovation_${innovationIndex + 1}`;
        const option = document.createElement('label');
        const radio = document.createElement('input');
        radio.type = 'radio';
        radio.name = `innovation-${gap.gap_id}`;
        radio.value = innovationId;
        const text = document.createElement('span');
        text.textContent = value;
        radio.addEventListener('change', () => {
          selectedInnovationId = innovationId;
          selectedInnovationText = value;
          choose.disabled = false;
        });
        option.append(radio, text);
        innovations.appendChild(option);
      });
      choose.addEventListener('click', () => {
        if (!selectedInnovationId) return;
        $$('.gap-card.selected').forEach((node) => node.classList.remove('selected'));
        gapCard.classList.add('selected');
        selected.textContent = `已选择空白：${gap.gap_statement}；创新点：${selectedInnovationText}。正在进入开题报告生成。`;
        selected.hidden = false;
        generateProposal(gap.gap_id, selectedInnovationId);
      });
      gapCard.append(label, statement, why, evidence);
      if (innovations.children.length > 1) gapCard.appendChild(innovations);
      gapCard.appendChild(choose);
      body.appendChild(gapCard);
    });
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      body.hidden = expanded;
    });
    card.append(toggle, body);
    list.appendChild(card);
  });

  if (!(data.top_subdirections || []).length) {
    const empty = document.createElement('p');
    empty.className = 'inline-empty';
    empty.textContent = '尚无可展示的小方向与研究空白；系统不会用模拟结果填充。';
    list.appendChild(empty);
  }
  (data.synthesis_limitations || []).forEach((value) => {
    const item = document.createElement('li');
    item.textContent = value;
    limitations.appendChild(item);
  });
  const gapBadge = $('#gap-nav-count');
  gapBadge.textContent = (data.top_subdirections || []).length;
  gapBadge.hidden = !(data.top_subdirections || []).length;
}

function renderProposalUnavailable(message, needsSettings = false) {
  $('#proposal-loading').hidden = true;
  $('#proposal-workflow').hidden = true;
  $('#proposal-content').hidden = true;
  const empty = $('#proposal-empty');
  empty.hidden = false;
  empty.querySelector('h3').textContent = '开题报告尚未生成';
  empty.querySelector('p').textContent = message;
  const action = empty.querySelector('button');
  action.dataset.view = needsSettings ? 'settings' : 'gaps';
  action.textContent = needsSettings ? '打开检索设置' : '返回方向与空白';
  $('#proposal-status').textContent = '未完成';
  $('#proposal-status').classList.remove('ready');
}

function setProposalStep(active, completed = []) {
  $$('[data-proposal-step]').forEach((node) => {
    node.classList.toggle('active', node.dataset.proposalStep === active);
    node.classList.toggle('complete', completed.includes(node.dataset.proposalStep));
  });
}

function panelLine(container, label, value, passed = null) {
  const line = document.createElement('p');
  line.textContent = `${label}：${value}`;
  if (passed === true) line.className = 'pass';
  if (passed === false) line.className = 'blocked';
  container.appendChild(line);
}

function renderWorkflowPanels(panels = {}) {
  const grid = $('#workflow-panel-grid');
  grid.hidden = false;
  const skill = $('#skill-panel');
  const evidence = $('#evidence-panel');
  const saturation = $('#saturation-panel');
  const audit = $('#audit-panel');
  [skill, evidence, saturation, audit].forEach((node) => { node.innerHTML = ''; });
  (panels.skill?.items || []).forEach((item) => {
    const passed = item.status === 'PASS' || item.status === 'READY_FOR_HUMAN_REVIEW';
    panelLine(skill, item.label, item.status, passed ? true : null);
  });
  panelLine(evidence, 'Claim', panels.evidence?.claim_count ?? 0, (panels.evidence?.claim_count ?? 0) > 0);
  panelLine(evidence, '证据绑定', panels.evidence?.binding_count ?? 0, (panels.evidence?.binding_count ?? 0) > 0);
  panelLine(evidence, '证据层级', JSON.stringify(panels.evidence?.evidence_levels || {}));
  panelLine(evidence, '仅正式证据', panels.evidence?.formal_only ? '是' : '否', Boolean(panels.evidence?.formal_only));
  panelLine(saturation, '状态', panels.saturation?.status || 'NOT_AVAILABLE');
  panelLine(saturation, '门禁权', panels.saturation?.advisory_only ? '仅建议，不改门槛' : '异常');
  panelLine(audit, 'Claim Audit', panels.audit?.claim_valid ? '通过' : '待通过', Boolean(panels.audit?.claim_valid));
  panelLine(audit, 'Citation Audit', panels.audit?.citation_valid ? '通过' : '待生成');
  panelLine(audit, '跨节一致性', panels.audit?.consistency_valid ? '通过' : '待生成');
  panelLine(audit, '任务卡', panels.audit?.task_cards_valid ? '通过' : '待确认');
  panelLine(audit, '状态上限', panels.audit?.release_ceiling || 'READY_FOR_HUMAN_REVIEW');
}

const constraintLabels = {
  degree_level: '学位与培养层次', institution_template: '学校模板要求', output_language: '写作语言',
  target_word_count: '目标字数', deadline: '截止时间', data_access: '数据权限',
  method_constraints: '方法限制', research_context: '研究情境', ethics_privacy: '伦理与隐私',
  tool_capabilities: '工具能力',
};

function renderConstraintReview(result) {
  const constraints = result.proposal?.user_constraints || {};
  state.proposalConstraints = constraints;
  $('#proposal-loading').hidden = true;
  $('#proposal-empty').hidden = true;
  $('#proposal-workflow').hidden = false;
  $('#proposal-content').hidden = true;
  $('#proposal-constraints-form').hidden = true;
  $('#proposal-plan-review').hidden = true;
  $('#proposal-constraint-review').hidden = false;
  $('#proposal-checkpoint-message').textContent = result.proposal_message || '请确认用户约束。';
  $('#proposal-status').textContent = '待确认用户约束';
  setProposalStep('constraints');
  const list = $('#constraint-review-list');
  list.innerHTML = '';
  Object.entries(constraintLabels).forEach(([key, label]) => {
    const row = document.createElement('div');
    const term = document.createElement('dt');
    const value = document.createElement('dd');
    term.textContent = label;
    value.textContent = String(constraints[key] ?? '—');
    row.append(term, value);
    list.appendChild(row);
  });
}

function renderPlanReview(result) {
  const proposal = result.proposal || {};
  state.proposalPlan = {
    research_design_blueprint: proposal.research_design_blueprint,
    proposal_outline: proposal.proposal_outline,
  };
  $('#proposal-loading').hidden = true;
  $('#proposal-empty').hidden = true;
  $('#proposal-workflow').hidden = false;
  $('#proposal-content').hidden = true;
  $('#proposal-constraints-form').hidden = true;
  $('#proposal-constraint-review').hidden = true;
  $('#proposal-plan-review').hidden = false;
  $('#proposal-checkpoint-message').textContent = result.proposal_message || '请确认蓝图和提纲。';
  $('#proposal-status').textContent = '待确认蓝图与提纲';
  setProposalStep('plan', ['constraints']);
  const blueprint = proposal.research_design_blueprint || {};
  const summary = $('#proposal-blueprint-summary');
  summary.innerHTML = '';
  [
    ['研究问题', blueprint.research_question], ['研究范式', blueprint.paradigm_id],
    ['分析单位', blueprint.unit_of_analysis], ['研究情境', blueprint.context],
    ['研究设计', blueprint.design], ['数据', blueprint.data], ['分析方法', blueprint.analysis],
    ['截止时间', blueprint.deadline],
  ].forEach(([label, value]) => {
    const card = document.createElement('div');
    const heading = document.createElement('strong');
    const text = document.createElement('span');
    heading.textContent = label;
    text.textContent = value || '尚未明确，不能静默补写';
    card.append(heading, text);
    summary.appendChild(card);
  });
  const outlineList = $('#proposal-outline-review');
  outlineList.innerHTML = '';
  (proposal.proposal_outline?.sections || []).forEach((section) => {
    const row = document.createElement('div');
    row.className = 'outline-row';
    const sequence = document.createElement('span');
    const title = document.createElement('strong');
    const target = document.createElement('small');
    sequence.textContent = String(section.sequence).padStart(2, '0');
    title.textContent = section.title;
    target.textContent = `${section.target_words}字`;
    row.append(sequence, title, target);
    outlineList.appendChild(row);
  });
}

function renderFinalProposal(result) {
  const proposal = result.proposal || {};
  const guidance = result.writing_guidance || {};
  const blueprint = proposal.research_design_blueprint || {};
  const titleSection = (proposal.sections || []).find((section) => section.section_id === 'working_title');
  $('#proposal-loading').hidden = true;
  $('#proposal-empty').hidden = true;
  $('#proposal-workflow').hidden = false;
  $('#proposal-constraints-form').hidden = true;
  $('#proposal-constraint-review').hidden = true;
  $('#proposal-plan-review').hidden = true;
  $('#proposal-checkpoint-message').textContent = result.proposal_message || '自动门禁完成，等待人工复核。';
  $('#proposal-content').hidden = false;
  const ready = result.proposal_status === 'READY_FOR_HUMAN_REVIEW';
  $('#proposal-status').textContent = ready ? '待人工复核' : '受控部分结果';
  $('#proposal-status').classList.toggle('ready', ready);
  setProposalStep('review', ['constraints', 'plan', 'generation']);
  $('#proposal-working-title').textContent = titleSection?.content || proposal.selected_gap?.gap_statement || '暂定题目待人工收敛';
  $('#proposal-research-question').textContent = blueprint.research_question
    ? '核心研究问题：' + blueprint.research_question
    : '核心研究问题未通过蓝图确认。';
  $('#proposal-paradigm').textContent = guidance.paradigm_label || guidance.paradigm_id || '—';
  $('#proposal-paradigm-status').textContent = guidance.paradigm_status
    ? '知识库状态：' + guidance.paradigm_status
    : '范式状态待核验';
  const audit = result.proposal_audit || {};
  $('#proposal-audit').textContent = `逐节生成 ${(proposal.sections || []).length} 节 · Claim ${audit.claim_audit?.claim_count || 0} 条 · 引用审计 ${audit.citation_audit?.valid ? '通过' : '未通过'}`;

  const sectionList = $('#proposal-sections');
  sectionList.innerHTML = '';
  (proposal.sections || []).forEach((section, index) => {
    const article = document.createElement('article');
    article.className = 'proposal-section';
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.className = 'proposal-section-toggle';
    toggle.setAttribute('aria-expanded', index === 0 ? 'true' : 'false');
    const number = document.createElement('span');
    number.textContent = String(index + 1).padStart(2, '0');
    const title = document.createElement('strong');
    title.textContent = section.title;
    const arrow = document.createElement('span');
    arrow.textContent = '⌄';
    toggle.append(number, title, arrow);
    const body = document.createElement('div');
    body.className = 'proposal-section-body';
    body.hidden = index !== 0;
    const content = document.createElement('p');
    content.textContent = section.content || '本节证据不足，尚未生成内容。';
    body.appendChild(content);
    if ((section.citations || []).length) {
      const evidence = document.createElement('div');
      evidence.className = 'section-evidence';
      const label = document.createElement('strong');
      label.textContent = '本节Claim与证据绑定';
      evidence.appendChild(label);
      section.citations.forEach((citation) => {
        const item = document.createElement('span');
        item.textContent = `${citation.claim_id} · ${citation.paper_id} · ${citation.evidence_span?.evidence_level || 'unknown'}`;
        evidence.appendChild(item);
      });
      body.appendChild(evidence);
    }
    if ((section.assumptions || []).length) {
      const assumptions = document.createElement('ul');
      assumptions.className = 'section-assumptions';
      section.assumptions.forEach((value) => {
        const item = document.createElement('li');
        item.textContent = value;
        assumptions.appendChild(item);
      });
      body.appendChild(assumptions);
    }
    toggle.addEventListener('click', () => {
      const expanded = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!expanded));
      body.hidden = expanded;
    });
    article.append(toggle, body);
    sectionList.appendChild(article);
  });

  const references = $('#proposal-references');
  references.innerHTML = '';
  const citationMap = new Map();
  (proposal.sections || []).forEach((section) => (section.citations || []).forEach((citation) => {
    citationMap.set(`${citation.claim_id}|${citation.paper_id}`, citation);
  }));
  [...citationMap.values()].forEach((citation, index) => {
    const item = document.createElement('p');
    const number = document.createElement('span');
    number.textContent = '[' + (index + 1) + ']';
    item.appendChild(number);
    item.appendChild(document.createTextNode(`${citation.claim_id} · ${citation.paper_id} · ${citation.evidence_span?.text || '证据句缺失'}`));
    references.appendChild(item);
  });

  const taskCardList = $('#proposal-task-cards');
  taskCardList.innerHTML = '';
  (proposal.execution_task_cards?.cards || []).forEach((task) => {
    const row = document.createElement('div');
    row.className = 'task-card-row';
    const title = document.createElement('strong');
    const meta = document.createElement('span');
    title.textContent = `${String(task.sequence).padStart(2, '0')} ${task.title}`;
    meta.textContent = `${task.status} · ${task.target_words}字 · ${task.controlled_inputs?.allowed_claim_ids?.length || 0}个允许Claim`;
    row.append(title, meta);
    taskCardList.appendChild(row);
  });

  const guidanceList = $('#guidance-stages');
  guidanceList.innerHTML = '';
  (guidance.stages || []).forEach((stage, index) => {
    const card = document.createElement('article');
    card.className = 'guidance-card';
    const heading = document.createElement('button');
    heading.type = 'button';
    heading.setAttribute('aria-expanded', index === 0 ? 'true' : 'false');
    const title = document.createElement('strong');
    title.textContent = stage.title;
    const purpose = document.createElement('small');
    purpose.textContent = stage.purpose || '本阶段指导待补充';
    const arrow = document.createElement('span');
    arrow.textContent = '⌄';
    heading.append(title, purpose, arrow);
    const body = document.createElement('div');
    body.className = 'guidance-body';
    body.hidden = index !== 0;
    [
      ['推荐结构 / Moves', stage.recommended_moves],
      ['必须呈现的证据', stage.evidence_required],
      ['常见失败', stage.common_failures],
      ['自检问题', stage.self_check],
    ].forEach(([labelText, values]) => {
      if (!values?.length) return;
      const label = document.createElement('h4');
      label.textContent = labelText;
      const list = document.createElement('ul');
      values.forEach((value) => {
        const item = document.createElement('li');
        item.textContent = value;
        list.appendChild(item);
      });
      body.append(label, list);
    });
    heading.addEventListener('click', () => {
      const expanded = heading.getAttribute('aria-expanded') === 'true';
      heading.setAttribute('aria-expanded', String(!expanded));
      body.hidden = expanded;
    });
    card.append(heading, body);
    guidanceList.appendChild(card);
  });

  const limitations = $('#proposal-limitations');
  limitations.innerHTML = '';
  (result.proposal_limitations || []).forEach((value) => {
    const item = document.createElement('li');
    item.textContent = value;
    limitations.appendChild(item);
  });
  const badge = $('#proposal-nav-state');
  badge.hidden = false;
  badge.textContent = '✓';
}

function renderProposal(result) {
  renderWorkflowPanels(result.workflow_panels || {});
  if (result.proposal_status === 'USER_CONSTRAINT_CONFIRMATION_REQUIRED') {
    renderConstraintReview(result);
    return;
  }
  if (result.proposal_status === 'PROPOSAL_PLAN_CONFIRMATION_REQUIRED') {
    renderPlanReview(result);
    return;
  }
  if (['READY_FOR_HUMAN_REVIEW', 'PROPOSAL_CONTROLLED_PARTIAL'].includes(result.proposal_status)) {
    renderFinalProposal(result);
    return;
  }
  if (result.proposal_status === 'PROPOSAL_NEEDS_USER_INPUT') {
    $('#proposal-loading').hidden = true;
    $('#proposal-workflow').hidden = false;
    $('#proposal-constraints-form').hidden = false;
    $('#proposal-checkpoint-message').textContent = result.proposal_message || '请补充用户约束。';
    setProposalStep('constraints');
    return;
  }
  renderProposalUnavailable(
    result.proposal_message || '当前没有可展示的正式开题结果。',
    result.proposal_status === 'PROPOSAL_NOT_CONFIGURED',
  );
}

function collectProposalConstraints() {
  return {
    degree_level: $('#constraint-degree').value,
    institution_template: $('#constraint-template').value,
    output_language: $('#constraint-language').value,
    target_word_count: Number($('#constraint-words').value),
    deadline: $('#constraint-deadline').value,
    data_access: $('#constraint-data').value,
    method_constraints: $('#constraint-method').value,
    research_context: $('#constraint-context').value,
    ethics_privacy: $('#constraint-ethics').value,
    tool_capabilities: $('#constraint-tools').value,
  };
}

async function requestProposal(extra = {}) {
  const contextId = state.data?.proposal_context_id;
  const selection = state.proposalSelection;
  if (!contextId || !selection) {
    renderProposalUnavailable('本次开题上下文未建立，请重新运行论文检索与五方向综合。');
    return;
  }
  $('#proposal-loading').hidden = false;
  $('#proposal-loading-title').textContent = extra.blueprint_confirmed ? '正在按确认计划逐节生成…' : '正在校验受控开题检查点…';
  $('#proposal-status').textContent = extra.blueprint_confirmed ? '逐节生成中' : '检查中';
  $('#proposal-status').classList.remove('ready');
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), 120000);
  try {
    const response = await fetch('/api/proposal', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        proposal_context_id: contextId,
        selected_gap_id: selection.gapId,
        selected_innovation_id: selection.innovationId,
        user_constraints: state.proposalConstraints || {},
        constraints_confirmed: false,
        blueprint_confirmed: false,
        outline_confirmed: false,
        ...extra,
      }),
      signal: controller.signal,
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.message_to_user || '开题报告生成失败');
    state.data.proposal_result = result;
    renderProposal(result);
  } catch (error) {
    const message = error.name === 'AbortError'
      ? '生成等待超过2分钟，已停止本次请求。已选空白和论文结果不受影响。'
      : error.message;
    renderProposalUnavailable(message);
  } finally {
    clearTimeout(timer);
  }
}

function generateProposal(gapId, innovationId) {
  state.proposalSelection = { gapId, innovationId };
  state.proposalConstraints = null;
  state.proposalPlan = null;
  switchView('proposal');
  $('#proposal-empty').hidden = true;
  $('#proposal-loading').hidden = true;
  $('#proposal-content').hidden = true;
  $('#workflow-panel-grid').hidden = true;
  $('#proposal-workflow').hidden = false;
  $('#proposal-constraints-form').reset();
  $('#proposal-constraints-form').hidden = false;
  $('#proposal-constraint-review').hidden = true;
  $('#proposal-plan-review').hidden = true;
  $('#proposal-checkpoint-message').textContent = '先确认会改变研究设计的用户约束；当前不会调用生成模型。';
  $('#proposal-status').textContent = '待填写用户约束';
  $('#proposal-status').classList.remove('ready');
  setProposalStep('constraints');
}

async function runSynthesis(jobId) {
  if (!jobId) {
    renderSynthesis(state.data);
    return;
  }
  $('#gaps-empty').hidden = true;
  $('#synthesis-results').hidden = false;
  setSynthesisNotice('论文已展示，正在后台归纳五个小方向与研究空白…');
  $('#synthesis-audit').textContent = '综合处理中';
  try {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 120000);
    const response = await fetch('/api/synthesize', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ job_id: jobId }),
      signal: controller.signal,
    });
    clearTimeout(timer);
    const result = await response.json();
    if (!response.ok) throw new Error(result.message_to_user || '方向综合失败');
    Object.assign(state.data, result);
    const synthesisStage = state.data.stages?.find((item) => item.id === 'synthesis');
    if (synthesisStage) synthesisStage.status = ['SYNTHESIS_COMPLETE', 'SYNTHESIS_PARTIAL'].includes(result.synthesis_status) ? 'complete' : 'blocked';
    renderPipeline(state.data.stages);
    renderSynthesis(state.data);
  } catch (error) {
    const message = error.name === 'AbortError'
      ? '方向综合等待超时。论文结果不受影响，可稍后重新检索后再试。'
      : error.message;
    setSynthesisNotice(message, false, true);
    $('#synthesis-audit').textContent = '综合未完成';
  }
}

async function submitResearch(event) {
  event.preventDefault();
  formError.textContent = '';
  if (!directionSelect.value) {
    formError.textContent = '请先选择研究大方向。';
    directionSelect.focus();
    return;
  }
  if (Number(zhCount.value) < 1 || Number(enCount.value) < 1) {
    formError.textContent = '中英文论文数量都必须是大于0的整数。';
    return;
  }

  setLoading(true);
  state.retrievalController = new AbortController();
  const timeout = setTimeout(() => state.retrievalController.abort(), 120000);
  try {
    const response = await fetch('/api/research', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      signal: state.retrievalController.signal,
      body: JSON.stringify({
        selected_direction_id: directionSelect.value,
        fine_grained_question: questionInput.value.trim() || null,
        chinese_count: Number(zhCount.value),
        english_count: Number(enCount.value),
        run_synthesis: false,
      }),
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.message_to_user || '请求失败');
    state.paperFilter = 'all';
    state.visiblePapers = PAGE_SIZE;
    renderDiscovery(data);
    if (['RETRIEVAL_COMPLETE', 'RETRIEVAL_PARTIAL'].includes(data.status_code)) {
      runSynthesis(data.synthesis_job_id);
    }
  } catch (error) {
    formError.textContent = error.name === 'AbortError'
      ? '检索等待超过2分钟，已停止本次请求。请检查网络后重试；系统不会把超时显示成零结果。'
      : error.message;
  } finally {
    clearTimeout(timeout);
    state.retrievalController = null;
    setLoading(false);
  }
}

function resetForm(clearResults = false) {
  form.reset();
  directionSelect.value = DEFAULT_DIRECTION;
  zhCount.value = 10;
  enCount.value = 20;
  formError.textContent = '';
  updateRoutePreview();
  if (clearResults) {
    state.data = null;
    $('#papers-empty').hidden = false;
    $('#paper-content').hidden = true;
    $('#gaps-empty').hidden = false;
    $('#synthesis-results').hidden = true;
    $('#proposal-empty').hidden = false;
    $('#proposal-workflow').hidden = true;
    $('#proposal-content').hidden = true;
    $('#proposal-loading').hidden = true;
    $('#workflow-panel-grid').hidden = true;
    $('#paper-nav-count').hidden = true;
    $('#gap-nav-count').hidden = true;
    $('#proposal-nav-state').hidden = true;
    $('#proposal-status').textContent = '尚未开始';
    $('#proposal-status').classList.remove('ready');
    state.proposalSelection = null;
    state.proposalConstraints = null;
    state.proposalPlan = null;
  }
  switchView('start');
}

document.addEventListener('click', (event) => {
  const viewButton = event.target.closest('[data-view]');
  if (viewButton) switchView(viewButton.dataset.view);
  const brandLink = event.target.closest('[data-view-link]');
  if (brandLink) {
    event.preventDefault();
    switchView(brandLink.dataset.viewLink);
  }
  if (event.target.closest('[data-new-research]')) resetForm(true);
});

questionInput.addEventListener('input', updateRoutePreview);
form.addEventListener('submit', submitResearch);
$('#proposal-constraints-form').addEventListener('submit', (event) => {
  event.preventDefault();
  if (!event.currentTarget.reportValidity()) return;
  state.proposalConstraints = collectProposalConstraints();
  requestProposal();
});
$('#confirm-proposal-constraints').addEventListener('click', () => {
  requestProposal({ constraints_confirmed: true });
});
$('#confirm-proposal-plan').addEventListener('click', () => {
  if (!state.proposalPlan) return;
  requestProposal({
    constraints_confirmed: true,
    research_design_blueprint: state.proposalPlan.research_design_blueprint,
    blueprint_confirmed: true,
    proposal_outline: state.proposalPlan.proposal_outline,
    outline_confirmed: true,
  });
});
$('#reset-button').addEventListener('click', () => resetForm(false));
$('#cancel-request').addEventListener('click', () => state.retrievalController?.abort());
configureApiButton.addEventListener('click', configureApi);
clearApiButton.addEventListener('click', clearApi);
configureRetrievalButton.addEventListener('click', configureRetrievalApi);
clearRetrievalButton.addEventListener('click', clearRetrievalApi);
$('#load-more').addEventListener('click', () => {
  state.visiblePapers += PAGE_SIZE;
  renderPaperList();
});
$$('[data-paper-filter]').forEach((button) => {
  button.addEventListener('click', () => {
    $$('[data-paper-filter]').forEach((node) => node.classList.remove('active'));
    button.classList.add('active');
    state.paperFilter = button.dataset.paperFilter;
    state.visiblePapers = PAGE_SIZE;
    renderPaperList();
  });
});

loadDirections().catch((error) => {
  directionSelect.innerHTML = '<option value="">知识库读取失败</option>';
  formError.textContent = error.message;
});
refreshApiState().catch((error) => {
  apiState.textContent = '状态异常';
  apiMessage.textContent = error.message;
  $('#service-status span').textContent = '服务连接异常';
  $('#service-status').classList.add('error');
});
