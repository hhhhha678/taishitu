const app = document.getElementById('app')

async function resolveDashboardData() {
  if (window.__DASHBOARD_DATA__) return window.__DASHBOARD_DATA__
  const res = await fetch('/api/dashboard')
  if (!res.ok) {
    throw new Error(`接口返回 ${res.status}`)
  }
  return res.json()
}

function panelTitle(title, extra = '') {
  return `
    <div class="panel-title">
      <h3>${title}</h3>
      ${extra ? `<span>${extra}</span>` : ''}
    </div>
  `
}

function renderShell(data) {
  const title = String(data.title || '').replace('感知大屏', '').trim()
  app.className = 'screen'
  app.innerHTML = `
    <header class="hero">
      <div>
        <h1>${title}</h1>
      </div>
      <div class="hero-meta">
        <div>历史时间范围</div>
        <strong>${data.date_range.from} 至 ${data.date_range.to}</strong>
      </div>
    </header>

    <section class="metrics-grid">
      ${data.metrics
        .map(
          (metric) => `
            <div class="metric-card">
              <span>${metric.label}</span>
              <strong>${Number(metric.value).toLocaleString()}</strong>
            </div>
          `,
        )
        .join('')}
    </section>

    <main class="content-grid">
      <aside class="left-rail">
        <section class="panel compact-panel">
          ${panelTitle('总体态度结构')}
          <div class="ring-panel-body">
            <div id="attitude-chart" class="ring-chart"></div>
            <div id="attitude-legend" class="ring-legend"></div>
          </div>
        </section>
        <section class="panel compact-panel">
          ${panelTitle('语种分布')}
          <div class="ring-panel-body">
            <div id="language-chart" class="ring-chart"></div>
            <div id="language-legend" class="ring-legend"></div>
          </div>
        </section>
        <section class="panel compact-panel focus-card">
          <div class="panel-title">
            <h3>当前焦点</h3>
            <button id="focus-toggle" class="focus-toggle" type="button">暂停轮播</button>
          </div>
          <div id="focus-card"></div>
        </section>
      </aside>

      <section class="map-panel">
        ${panelTitle('全国分省舆情热力态势')}
        <div class="map-layout">
          <div class="map-side">
            <div id="region-float" class="floating-region-card"></div>
            <div id="region-heat-strip" class="region-heat-strip"></div>
          </div>
          <div class="map-canvas-wrap">
            <div id="china-map" class="map-chart"></div>
          </div>
        </div>
      </section>

      <section class="feed-panel">
        ${panelTitle('历史原话动态流', '区域轮播同步')}
        <div id="feed-list" class="feed-list"></div>
      </section>
    </main>

    <section class="footer-grid">
      <section class="panel footer-panel">
        ${panelTitle('地区样本', '当前区域')}
        <div id="region-samples" class="sample-list"></div>
      </section>
      <section class="panel footer-panel">
        ${panelTitle('平台样本', '当前平台')}
        <div id="platform-samples" class="sample-list"></div>
      </section>
      <section class="panel footer-panel narrow-panel">
        ${panelTitle('平台舆情量排行')}
        <div id="platform-chart" class="chart-footer"></div>
      </section>
      <section class="panel footer-panel narrow-panel">
        ${panelTitle('非支持问题构成')}
        <div id="nonsupport-chart" class="chart-footer"></div>
      </section>
      <section class="panel footer-panel timeline-panel">
        ${panelTitle('历史时间轴回放')}
        <div id="timeline-chart" class="chart-footer"></div>
      </section>
    </section>
  `
}

function compactNumber(value) {
  const number = Number(value) || 0
  if (number >= 10000) return `${(number / 10000).toFixed(1)}万`
  return number.toLocaleString()
}

function barOption(rows, valueKey, activeName, options = {}) {
  const {
    left = 132,
    right = 46,
    top = 10,
    bottom = 10,
    labelWidth = 124,
    labelFontSize = 10,
    valueFontSize = 10,
    barWidth = 10,
  } = options
  return {
    animationDuration: 500,
    grid: { left, right, top, bottom },
    xAxis: {
      type: 'value',
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(124, 200, 239, 0.1)' } },
    },
    yAxis: {
      type: 'category',
      axisLabel: {
        color: '#d8efff',
        fontSize: labelFontSize,
        overflow: 'truncate',
        width: labelWidth,
      },
      data: rows.map((item) => item.name),
    },
    series: [
      {
        type: 'bar',
        data: rows.map((item) => ({
          value: item[valueKey],
          itemStyle: { color: item.name === activeName ? '#ffd166' : '#2bb3ff' },
        })),
        label: {
          show: true,
          position: 'right',
          color: '#eaf7ff',
          fontSize: valueFontSize,
          formatter: (params) => compactNumber(params.value),
        },
        barWidth,
      },
    ],
  }
}

function ringOption(rows, options = {}) {
  const { compact = false, radius, center } = options
  return {
    animationDuration: 500,
    color: ['#5b75d6', '#85d86f', '#ffc043', '#43c9ff', '#d77cff', '#ff8a63'],
    tooltip: { trigger: 'item' },
    legend: { show: false },
    series: [
      {
        type: 'pie',
        radius: radius || (compact ? ['52%', '74%'] : ['42%', '62%']),
        center: center || (compact ? ['50%', '42%'] : ['50%', '46%']),
        minAngle: compact ? 4 : 0,
        itemStyle: {
          borderColor: '#0b2136',
          borderWidth: compact ? 1.4 : 1,
        },
        label: compact
          ? { show: false }
          : { color: '#f3fbff', fontSize: 10, formatter: '{b}\n{c}' },
        data: rows,
      },
    ],
  }
}

function renderRingLegend(targetId, rows) {
  const colors = ['#5b75d6', '#85d86f', '#ffc043', '#43c9ff', '#d77cff', '#ff8a63']
  const node = document.getElementById(targetId)
  if (!node) return
  node.innerHTML = rows
    .map(
      (item, index) => `
        <span class="ring-legend-item">
          <i style="background:${colors[index % colors.length]}"></i>
          <b>${item.name}</b>
          <em>${Number(item.value || 0).toLocaleString()}</em>
        </span>
      `,
    )
    .join('')
}

function timelineOption(rows, activeIndex) {
  return {
    animationDuration: 500,
    tooltip: { trigger: 'axis' },
    grid: { left: 34, right: 10, top: 18, bottom: 22 },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.date.slice(5)),
      axisLabel: { color: '#8dd8ff', fontSize: 10 },
      axisLine: { lineStyle: { color: '#2b6d9b' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#8dd8ff', fontSize: 10 },
      splitLine: { lineStyle: { color: 'rgba(124, 200, 239, 0.1)' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: rows.map((item) => item.count),
        symbolSize: rows.map((_, idx) => (idx === activeIndex ? 8 : 5)),
        lineStyle: { color: '#33c2ff', width: 2.5 },
        itemStyle: { color: '#ffd166' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(51, 194, 255, 0.28)' },
            { offset: 1, color: 'rgba(51, 194, 255, 0)' },
          ]),
        },
      },
    ],
  }
}

function mapOption(provinceHeat, regions, activeRegion) {
  const highlighted = new Set(activeRegion?.provinces || [])
  const provinceAliases = {
    北京: '北京市',
    天津: '天津市',
    上海: '上海市',
    重庆: '重庆市',
    内蒙古: '内蒙古自治区',
    广西: '广西壮族自治区',
    西藏: '西藏自治区',
    宁夏: '宁夏回族自治区',
    新疆: '新疆维吾尔自治区',
  }
  const heatData = provinceHeat.flatMap((item) => {
    const alias = provinceAliases[item.name]
    return alias ? [item, { ...item, name: alias }] : [item]
  })
  const isHighlighted = (name) => highlighted.has(name) || Object.entries(provinceAliases).some(([shortName, fullName]) => highlighted.has(shortName) && name === fullName)
  const labelCoords = {
    新疆: { coord: [85.2, 41.2], position: 'right', distance: 6 },
    '青海、西藏': { coord: [91.5, 32.4], position: 'right', distance: 6 },
    '四川、甘肃民族地区': { coord: [103.0, 33.1], position: 'right', distance: 6 },
    '内蒙古、河北及东北': { coord: [118.6, 43.0], position: 'right', distance: 6 },
    云南西部民族地区: { coord: [98.8, 25.3], position: 'left', distance: 6 },
    云南东中部民族地区: { coord: [103.5, 24.5], position: 'right', distance: 6 },
    北京: { coord: [116.4, 40.4], position: 'top', distance: 8 },
    天津: { coord: [117.7, 38.7], position: 'bottom', distance: 8 },
    河南: { coord: [113.6, 34.7], position: 'right', distance: 6 },
    江西: { coord: [115.9, 27.6], position: 'right', distance: 6 },
    广东: { coord: [113.3, 23.1], position: 'right', distance: 6 },
    广西: { coord: [108.3, 23.8], position: 'left', distance: 6 },
  }
  const regionLabels = (regions || [])
    .map((region) => {
      const label = labelCoords[region.name]
      if (!label) return null
      return {
        name: region.name,
        value: region.total,
        coord: label.coord,
        label: {
          position: label.position,
          distance: label.distance,
        },
      }
    })
    .filter(Boolean)
  return {
    animationDuration: 600,
    tooltip: {
      trigger: 'item',
      formatter: (params) => {
        const value = params.value ?? 0
        return `${params.name}<br/>舆情量：${value}`
      },
    },
    visualMap: {
      min: 0,
      max: Math.max(...provinceHeat.map((item) => item.value), 1),
      show: false,
      calculable: false,
      inRange: {
        color: ['#123451', '#185b81', '#2196d3', '#7fd6ff'],
      },
    },
    series: [
      {
        name: '省份热力',
        type: 'map',
        map: 'china',
        roam: false,
        zoom: 1.08,
        layoutCenter: ['48%', '48%'],
        layoutSize: '138%',
        aspectScale: 0.9,
        top: '-12%',
        left: '-12%',
        right: '-12%',
        bottom: '-12%',
        selectedMode: false,
        label: {
          show: false,
          color: '#dfefff',
        },
        itemStyle: {
          areaColor: '#10304f',
          borderColor: '#7dc9ff',
          borderWidth: 0.9,
        },
        emphasis: {
          label: { show: true, color: '#ffffff', fontSize: 10 },
          itemStyle: {
            areaColor: '#ffd166',
            borderColor: '#fff1b6',
            borderWidth: 1.3,
          },
        },
        data: heatData.map((item) => ({
          ...item,
          itemStyle: isHighlighted(item.name)
            ? {
                areaColor: '#ffd166',
                borderColor: '#fff4c8',
                borderWidth: 1.7,
                shadowColor: 'rgba(255, 209, 102, 0.45)',
                shadowBlur: 10,
              }
            : undefined,
        })),
        markPoint: {
          symbol: 'circle',
          symbolSize: 4,
          silent: true,
          label: {
            show: true,
            position: 'right',
            distance: 6,
            color: '#f4fbff',
            fontSize: 11,
            fontWeight: 700,
            padding: [3, 6],
            borderRadius: 4,
            backgroundColor: 'rgba(7, 28, 47, 0.74)',
            borderColor: 'rgba(126, 196, 236, 0.36)',
            borderWidth: 1,
            formatter: (params) => `${params.name} ${compactNumber(params.value)}`,
          },
          itemStyle: {
            color: '#ffd166',
            shadowColor: 'rgba(255, 209, 102, 0.45)',
            shadowBlur: 8,
          },
          data: regionLabels,
        },
      },
    ],
  }
}

function toComment(item) {
  return `<article class="feed-item">
    <div class="feed-head">
      <span>${item.date || '历史样本'}</span>
      <span>${item.platform}</span>
      <span>${item.region}</span>
      <b>${item.attitude}</b>
    </div>
    <p>${item.text}</p>
  </article>`
}

function normalizeLanguageToken(name) {
  const token = name.replace('（含原未标注语言）', '').replace('/其他', '').replace('/文', '')
  const aliases = {
    '中文/普通话': '汉',
    '维吾尔语': '维吾尔',
    '藏语': '藏',
    '彝语': '彝',
    '蒙古语': '蒙古',
    '表情符号': '表情',
  }
  return aliases[token] || token
}

function renderFocus(activePlatform, activeLanguage, activeRegion, activeTimeline) {
  const platformAttitudes = (activePlatform.attitudes || []).filter((item) => item.value > 0)
  const regionAttitudes = (activeRegion.attitudes || []).filter((item) => item.value > 0)
  const maxValue = Math.max(...platformAttitudes.map((item) => item.value), 1)
  const attitudeBars = platformAttitudes
    .slice(0, 8)
    .map(
      (item) => `
        <div class="mini-bar">
          <span>${item.name}</span>
          <i style="width:${Math.max((item.value / maxValue) * 100, 2)}%"></i>
          <strong>${Number(item.value).toLocaleString()}</strong>
        </div>
      `,
    )
    .join('')
  const regionMaxValue = Math.max(...regionAttitudes.map((item) => item.value), 1)
  const regionBars = regionAttitudes
    .slice(0, 8)
    .map(
      (item) => `
        <div class="mini-bar">
          <span>${item.name}</span>
          <i style="width:${Math.max((item.value / regionMaxValue) * 100, 2)}%"></i>
          <strong>${Number(item.value).toLocaleString()}</strong>
        </div>
      `,
    )
    .join('')
  document.getElementById('focus-card').innerHTML = `
    <div class="focus-row"><span>当前区域</span><strong>${activeRegion.name}</strong></div>
    <div class="focus-row"><span>舆情热度</span><strong>${activeRegion.total}</strong></div>
    <div class="focus-row"><span>当前平台</span><strong>${activePlatform.name}</strong></div>
    <div class="focus-row"><span>平台占比</span><strong>${(activePlatform.share * 100).toFixed(1)}%</strong></div>
    <div class="focus-row"><span>支持/非支持</span><strong>${activePlatform.support} / ${activePlatform.non_support}</strong></div>
    <div class="focus-row"><span>来源/查看</span><strong>${activePlatform.source_count} / ${activePlatform.view_count}</strong></div>
    <div class="focus-row"><span>当前语种</span><strong>${activeLanguage.name}</strong></div>
    <div class="focus-row"><span>语种样本</span><strong>${activeLanguage.value}</strong></div>
    <div class="focus-row"><span>时间轴</span><strong>${activeTimeline.date}</strong></div>
    <div class="mini-section-title">平台态度标签</div>
    <div class="mini-bar-list">${attitudeBars}</div>
    <div class="mini-section-title">地区态度标签</div>
    <div class="mini-bar-list">${regionBars}</div>
  `
}

function renderRegionFloat(region) {
  const provinces = (region.provinces || []).join('、') || region.name
  const topPlatforms = (region.top_platforms || [])
    .slice(0, 3)
    .map((item) => `<span>${item.name}<b>${item.value}</b></span>`)
    .join('')
  document.getElementById('region-float').innerHTML = `
    <div class="region-name">${region.name}</div>
    <div class="region-number">${region.total}</div>
    <div class="region-meta">支持 ${region.support} | 非支持 ${region.non_support}</div>
    <div class="region-note">涉及省份：${provinces}</div>
    <div class="region-platforms">${topPlatforms ? `<em>主要平台</em>${topPlatforms}` : '<em>主要平台</em><span>暂无可归属平台样本</span>'}</div>
  `
}

function renderRegionHeatStrip(regions, activeRegion) {
  const rows = regions
  document.getElementById('region-heat-strip').innerHTML = rows
    .map(
      (item, index) => `
        <div class="heat-row ${item.name === activeRegion.name ? 'active' : ''}" data-region-name="${item.name}">
          <span>${index + 1}. ${item.name}</span>
          <strong>${item.total}</strong>
        </div>
      `,
    )
    .join('')
}

function renderSamples(data, activeRegion, activePlatform, activeLanguage) {
  const linkedSamples = uniqueSamples(pickFeed(data.feed, {
    activeRegion,
    activePlatform,
    activeDate: null,
    regionStrict: true,
    platformStrict: true,
  }))
    .slice(-2)
    .reverse()
  const regionOnlyPool = uniqueSamples(pickFeed(data.feed, {
    activeRegion,
    activePlatform,
    activeDate: null,
    regionStrict: true,
    platformStrict: false,
  }))
  const regionOnlySamples = randomPick(regionOnlyPool, adaptiveSampleCount(regionOnlyPool))
  const platformOnlyPool = uniqueSamples(pickFeed(data.feed, {
    activeRegion,
    activePlatform,
    activeDate: null,
    regionStrict: false,
    platformStrict: true,
  }).filter((item) => item.region_group !== activeRegion.name && item.region !== activeRegion.name))
  const platformOnlySamples = randomPick(platformOnlyPool, adaptiveSampleCount(platformOnlyPool))
  const fallbackRegion = uniqueSamples(activeRegion.sample_comments || [])
  const fallbackPlatform = uniqueSamples(activePlatform.sample_comments || [])
  const regionSamples = regionOnlySamples.length
    ? regionOnlySamples
    : randomPick(fallbackRegion, adaptiveSampleCount(fallbackRegion))
  const platformSamples = platformOnlySamples.length
    ? platformOnlySamples
    : linkedSamples.length
      ? randomPick(linkedSamples, adaptiveSampleCount(linkedSamples))
      : randomPick(fallbackPlatform, adaptiveSampleCount(fallbackPlatform))
  const displayRegionSamples = randomPick(regionSamples, adaptiveSampleCount(regionSamples))
  const displayPlatformSamples = randomPick(platformSamples, adaptiveSampleCount(platformSamples))
  const regionSampleNode = document.getElementById('region-samples')
  const platformSampleNode = document.getElementById('platform-samples')
  regionSampleNode.className = `sample-list sample-count-${Math.min(Math.max(displayRegionSamples.length || 1, 1), 4)}`
  platformSampleNode.className = `sample-list sample-count-${Math.min(Math.max(displayPlatformSamples.length || 1, 1), 4)}`

  regionSampleNode.innerHTML = displayRegionSamples.length
    ? displayRegionSamples.map((item) => sampleItem(item, `${item.platform || item.platform_group}｜${item.region || item.region_group}`, item.attitude)).join('')
    : '<div class="sample-empty">当前地区暂无可展示样本</div>'

  platformSampleNode.innerHTML = displayPlatformSamples.length
    ? displayPlatformSamples
        .map((item) => sampleItem(item, `${item.region || item.region_group}｜${item.platform || item.platform_group}`, item.attitude))
        .join('')
    : '<div class="sample-empty">当前平台暂无可展示样本</div>'

  const regionTitle = document.querySelector('.footer-panel:nth-child(1) .panel-title span')
  if (regionTitle) regionTitle.textContent = activeRegion.name
  const platformTitle = document.querySelector('.footer-panel:nth-child(2) .panel-title span')
  if (platformTitle) platformTitle.textContent = activePlatform.name
}

function uniqueSamples(items) {
  const seen = new Set()
  return items.filter((item) => {
    const key = [item.date, item.platform, item.region, item.attitude, item.text].join('|')
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
}

function randomPick(items, count) {
  if (!items.length || count <= 0) return []
  const pool = [...items]
  for (let index = pool.length - 1; index > 0; index -= 1) {
    const swapIndex = Math.floor(Math.random() * (index + 1))
    const current = pool[index]
    pool[index] = pool[swapIndex]
    pool[swapIndex] = current
  }
  return pool.slice(0, Math.min(count, pool.length))
}

function adaptiveSampleCount(items) {
  if (!items.length) return 2
  const lengths = items.slice(0, 6).map((item) => sampleText(item).length)
  const averageLength = lengths.reduce((sum, length) => sum + length, 0) / lengths.length
  const maxLength = Math.max(...lengths)
  if (maxLength <= 24 && averageLength <= 20) return 4
  if (maxLength <= 54 && averageLength <= 38) return 3
  return 2
}

function adaptiveFeedCount(items) {
  if (!items.length) return 3
  const averageLength = items.slice(0, 5).reduce((sum, item) => sum + String(item.text || '').length, 0) / Math.min(items.length, 5)
  if (averageLength <= 32) return 5
  if (averageLength <= 78) return 4
  return 3
}

function sampleText(item) {
  return String(item.text || item.content || item.comment || item.original || item.raw_text || '')
}

function sampleItem(item, label, attitude = '') {
  return `<div class="sample-item">
    <span>${label}${attitude ? `｜${attitude}` : ''}</span>
    <div>${sampleText(item)}</div>
  </div>`
}

function findRegionIndexByProvince(regions, provinceName) {
  return regions.findIndex((item) => (item.provinces || []).includes(provinceName) || item.name === provinceName)
}

function findPlatformIndexByName(platforms, platformName) {
  return platforms.findIndex((item) => item.name === platformName)
}

function findTopRegionIndexForPlatform(data, platformName) {
  const counts = new Map()
  data.feed.forEach((item) => {
    if (item.platform_group !== platformName && item.platform !== platformName) return
    if (!item.region_group) return
    counts.set(item.region_group, (counts.get(item.region_group) || 0) + 1)
  })
  const [regionName] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0] || []
  return data.map.regions.findIndex((item) => item.name === regionName)
}

function timelineFocusPatch(data, timelineItem) {
  const patch = {}
  const regionIndex = data.map.regions.findIndex((item) => item.name === timelineItem.top_region)
  const platformIndex = data.platforms.findIndex((item) => item.name === timelineItem.top_platform)
  if (regionIndex >= 0) patch.regionIndex = regionIndex
  if (platformIndex >= 0) patch.platformIndex = platformIndex
  return patch
}

function applyRegionFocus(data, regionIndex, setState) {
  if (regionIndex < 0) return
  setState({
    regionIndex,
  })
}

function applyPlatformFocus(data, platformIndex, setState) {
  if (platformIndex < 0) return
  const platform = data.platforms[platformIndex]
  const regionIndex = findTopRegionIndexForPlatform(data, platform.name)
  setState({
    platformIndex,
    regionIndex: regionIndex >= 0 ? regionIndex : undefined,
  })
}

function pickFeed(feed, criteria) {
  return feed.filter((item) => {
    if (criteria.dateStrict && criteria.activeDate && item.date !== criteria.activeDate) return false
    if (criteria.activeDate && item.date && item.date > criteria.activeDate) return false
    if (criteria.regionStrict && criteria.activeRegion) {
      if (item.region_group !== criteria.activeRegion.name && item.region !== criteria.activeRegion.name) return false
    }
    if (criteria.platformStrict && criteria.activePlatform) {
      if (item.platform_group !== criteria.activePlatform.name && item.platform !== criteria.activePlatform.name) return false
    }
    return true
  })
}

function renderFeed(feed, activeRegion, activePlatform, activeDate) {
  const strategies = [
    { dateStrict: true, regionStrict: true, platformStrict: true, label: '当天地区×平台样本' },
    { dateStrict: true, regionStrict: true, platformStrict: false, label: '当天地区样本' },
    { dateStrict: true, regionStrict: false, platformStrict: true, label: '当天平台样本' },
    { dateStrict: true, regionStrict: false, platformStrict: false, label: '当天全局样本' },
    { regionStrict: true, platformStrict: true, label: '地区×平台交叉匹配' },
    { regionStrict: true, platformStrict: false, label: '当前地区历史样本' },
    { regionStrict: false, platformStrict: true, label: '当前平台历史样本' },
    { regionStrict: false, platformStrict: false, label: '全局历史样本' },
  ]

  let visible = []
  let sourceLabel = ''
  for (const strategy of strategies) {
    const pool = pickFeed(feed, {
      ...strategy,
      activeDate,
      activeRegion,
      activePlatform,
    })
    visible = randomPick(pool, adaptiveFeedCount(pool))
    if (visible.length) {
      sourceLabel = strategy.label
      break
    }
  }

  document.getElementById('feed-list').innerHTML = visible.length
    ? visible.map(toComment).join('')
    : '<div class="sample-empty">当前轮播区域暂无匹配原话</div>'

  const feedTitle = document.querySelector('.feed-panel .panel-title span')
  if (feedTitle) {
    feedTitle.textContent = `${activeDate}｜${sourceLabel}`
  }
}

async function boot() {
  const data = await resolveDashboardData()
  renderShell(data)

  let activeRegionIndex = 0
  let activePlatformIndex = 0
  let activeLanguageIndex = 0
  let activeTimelineIndex = 0
  let rotationPaused = false

  const setFocusState = (next) => {
    if (Number.isInteger(next.regionIndex)) activeRegionIndex = next.regionIndex
    if (Number.isInteger(next.platformIndex)) activePlatformIndex = next.platformIndex
    if (Number.isInteger(next.languageIndex)) activeLanguageIndex = next.languageIndex
    if (Number.isInteger(next.timelineIndex)) activeTimelineIndex = next.timelineIndex
    repaint()
  }

  const platformChart = echarts.init(document.getElementById('platform-chart'))
  const languageChart = echarts.init(document.getElementById('language-chart'))
  const mapChart = echarts.init(document.getElementById('china-map'))
  const attitudeChart = echarts.init(document.getElementById('attitude-chart'))
  const nonsupportChart = echarts.init(document.getElementById('nonsupport-chart'))
  const timelineChart = echarts.init(document.getElementById('timeline-chart'))

  languageChart.setOption(
    ringOption(data.languages.map((item) => ({ name: item.name, value: item.value })), {
      compact: true,
    }),
  )
  attitudeChart.setOption(ringOption(data.overall_attitudes, { compact: true }))
  renderRingLegend('language-legend', data.languages.map((item) => ({ name: item.name, value: item.value })))
  renderRingLegend('attitude-legend', data.overall_attitudes)

  function repaint() {
    const activeRegion = data.map.regions[activeRegionIndex]
    const activePlatform = data.platforms[activePlatformIndex]
    const activeLanguage = data.languages[activeLanguageIndex]
    const activeTimeline = data.timeline[activeTimelineIndex]
    const nonsupportActive = data.non_support_breakdown[activeTimelineIndex % data.non_support_breakdown.length]

    platformChart.setOption(
      barOption(data.platforms.slice(0, 7), 'total', activePlatform.name, {
        left: 128,
        right: 68,
        top: 16,
        bottom: 8,
        labelWidth: 116,
        labelFontSize: 11,
        valueFontSize: 12,
        barWidth: 12,
      }),
      true,
    )
    mapChart.setOption(mapOption(data.map.province_heat, data.map.regions, activeRegion), true)
    nonsupportChart.setOption(barOption(data.non_support_breakdown, 'value', nonsupportActive.name), true)
    timelineChart.setOption(timelineOption(data.timeline, activeTimelineIndex), true)

    renderFocus(activePlatform, activeLanguage, activeRegion, activeTimeline)
    renderRegionFloat(activeRegion)
    renderRegionHeatStrip(data.map.regions, activeRegion)
    renderFeed(data.feed, activeRegion, activePlatform, activeTimeline.date)
    renderSamples(data, activeRegion, activePlatform, activeLanguage)
    document.querySelectorAll('.heat-row').forEach((node) => {
      node.addEventListener('click', () => {
        const index = data.map.regions.findIndex((item) => item.name === node.dataset.regionName)
        applyRegionFocus(data, index, setFocusState)
      })
    })

    const timelineTitle = document.querySelector('.timeline-panel .panel-title span')
    if (timelineTitle) {
      timelineTitle.textContent = `${activeTimeline.top_region} | ${activeTimeline.top_platform}`
    }
  }

  repaint()

  const focusToggle = document.getElementById('focus-toggle')
  focusToggle.addEventListener('click', () => {
    rotationPaused = !rotationPaused
    focusToggle.textContent = rotationPaused ? '继续轮播' : '暂停轮播'
    focusToggle.classList.toggle('paused', rotationPaused)
  })

  platformChart.on('click', (params) => {
    const index = data.platforms.findIndex((item) => item.name === params.name)
    applyPlatformFocus(data, index, setFocusState)
  })

  languageChart.on('click', (params) => {
    const index = data.languages.findIndex((item) => item.name === params.name)
    if (index >= 0) setFocusState({ languageIndex: index })
  })

  mapChart.on('click', (params) => {
    const index = findRegionIndexByProvince(data.map.regions, params.name)
    applyRegionFocus(data, index, setFocusState)
  })

  timelineChart.on('click', (params) => {
    const index = data.timeline.findIndex((item) => item.date.slice(5) === params.name || item.date === params.name)
    if (index >= 0) setFocusState({ timelineIndex: index, ...timelineFocusPatch(data, data.timeline[index]) })
  })

  setInterval(() => {
    if (rotationPaused) return
    applyRegionFocus(data, (activeRegionIndex + 1) % data.map.regions.length, setFocusState)
  }, 9000)
  setInterval(() => {
    if (rotationPaused) return
    applyPlatformFocus(data, (activePlatformIndex + 1) % data.platforms.length, setFocusState)
  }, 11000)
  setInterval(() => {
    if (rotationPaused) return
    setFocusState({ languageIndex: (activeLanguageIndex + 1) % data.languages.length })
  }, 13000)
  setInterval(() => {
    if (rotationPaused) return
    const timelineIndex = (activeTimelineIndex + 1) % data.timeline.length
    setFocusState({ timelineIndex, ...timelineFocusPatch(data, data.timeline[timelineIndex]) })
  }, 8000)

  window.addEventListener('resize', () => {
    platformChart.resize()
    languageChart.resize()
    mapChart.resize()
    attitudeChart.resize()
    nonsupportChart.resize()
    timelineChart.resize()
  })
}

boot().catch((error) => {
  app.className = 'loading'
  app.textContent = `大屏加载失败：${error.message}`
})
