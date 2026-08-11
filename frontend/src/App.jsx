import { useEffect, useRef, useState } from 'react'
import * as echarts from 'echarts'
import 'echarts/map/js/china'

function useChart(option, deps = [], onReady) {
  const ref = useRef(null)
  const chartRef = useRef(null)

  useEffect(() => {
    if (!ref.current) return
    const chart = echarts.init(ref.current)
    chartRef.current = chart
    chart.setOption(option)
    if (onReady) onReady(chart)
    const resize = () => chart.resize()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      chart.dispose()
      chartRef.current = null
    }
  }, [])

  useEffect(() => {
    if (chartRef.current) {
      chartRef.current.setOption(option, true)
    }
  }, deps)

  return ref
}

function MetricCard({ metric }) {
  return (
    <div className="metric-card">
      <span>{metric.label}</span>
      <strong>{metric.value.toLocaleString()}</strong>
    </div>
  )
}

function PanelTitle({ title, extra }) {
  return (
    <div className="panel-title">
      <h3>{title}</h3>
      {extra && <span>{extra}</span>}
    </div>
  )
}

function compactNumber(value) {
  const number = Number(value) || 0
  if (number >= 10000) return `${(number / 10000).toFixed(1)}万`
  return number.toLocaleString()
}

function MapPanel({ data, activeRegionIndex, onRegionSelect }) {
  const region = data.regions[activeRegionIndex] || data.regions[0]
  const option = {
    backgroundColor: 'transparent',
    tooltip: {
      trigger: 'item',
      formatter: ({ name, value }) => `${name}<br/>舆情量 ${value || 0}`,
    },
    visualMap: {
      min: 0,
      max: Math.max(...data.province_heat.map((item) => item.value), 1),
      text: ['高', '低'],
      calculable: true,
      realtime: false,
      orient: 'vertical',
      right: 8,
      bottom: 12,
      textStyle: { color: '#d9f2ff' },
      inRange: { color: ['#15324b', '#0d8bd8', '#ffd166'] },
    },
    series: [
      {
        type: 'map',
        map: 'china',
        roam: false,
        zoom: 1.02,
        label: { show: false },
        itemStyle: {
          areaColor: '#0e2334',
          borderColor: '#2b6d9b',
          borderWidth: 1,
        },
        emphasis: {
          label: { show: false },
          itemStyle: { areaColor: '#31b2ff' },
        },
        data: data.province_heat,
      },
    ],
  }

  const ref = useChart(option, [data], (chart) => {
    chart.on('click', (params) => {
      const index = data.regions.findIndex((item) => item.provinces.includes(params.name) || item.name === params.name)
      if (index >= 0 && onRegionSelect) onRegionSelect(index)
    })
    if (!region) return
    region.provinces.forEach((province) => {
      chart.dispatchAction({ type: 'highlight', name: province })
    })
  })

  useEffect(() => {
    const chart = echarts.getInstanceByDom(ref.current)
    if (!chart) return
    chart.dispatchAction({ type: 'downplay', seriesIndex: 0 })
    if (!region) return
    region.provinces.forEach((province) => {
      chart.dispatchAction({ type: 'highlight', name: province })
      chart.dispatchAction({ type: 'showTip', seriesIndex: 0, name: province })
    })
  }, [activeRegionIndex, data, ref, region])

  return (
    <section className="map-panel">
      <PanelTitle title="全国地区热力态势" extra={region ? `当前高亮：${region.name}` : ''} />
      <div className="map-wrap">
        <div ref={ref} className="map-canvas" />
        {region && (
          <div className="floating-region-card">
            <div className="region-name">{region.name}</div>
            <div className="region-number">{region.total}</div>
            <div className="region-meta">支持 {region.support} ｜ 非支持 {region.non_support}</div>
          </div>
        )}
      </div>
    </section>
  )
}

function BarChart({ title, rows, valueKey = 'value', nameKey = 'name', activeName, onSelect }) {
  const option = {
    grid: { left: 100, right: 20, top: 20, bottom: 20 },
    xAxis: {
      type: 'value',
      axisLabel: { show: false },
      axisTick: { show: false },
      axisLine: { show: false },
      splitLine: { lineStyle: { color: 'rgba(124, 200, 239, 0.12)' } },
    },
    yAxis: {
      type: 'category',
      axisLabel: { color: '#d8efff' },
      data: rows.map((item) => item[nameKey]),
    },
    series: [
      {
        type: 'bar',
        data: rows.map((item) => ({
          value: item[valueKey],
          itemStyle: {
            color: item[nameKey] === activeName ? '#ffd166' : '#2bb3ff',
          },
        })),
        label: {
          show: true,
          position: 'right',
          color: '#eaf7ff',
          formatter: (params) => compactNumber(params.value),
        },
        barWidth: 14,
      },
    ],
  }
  const ref = useChart(option, [rows, activeName], (chart) => {
    chart.on('click', (params) => {
      const index = rows.findIndex((item) => item[nameKey] === params.name)
      if (index >= 0 && onSelect) onSelect(index, rows[index])
    })
  })
  return (
    <section className="side-panel">
      <PanelTitle title={title} />
      <div ref={ref} className="chart-small" />
    </section>
  )
}

function RingChart({ title, rows, onSelect, showPercentLegend = false }) {
  const total = rows.reduce((sum, item) => sum + Number(item.value || 0), 0) || 1
  const option = {
    tooltip: { trigger: 'item' },
    legend: {
      bottom: 0,
      textStyle: { color: '#d8efff' },
      formatter: (name) => {
        const row = rows.find((item) => item.name === name)
        const shortName = name.length > 10 ? `${name.slice(0, 10)}...` : name
        if (!showPercentLegend || !row) return shortName
        const percent = ((Number(row.value || 0) / total) * 100).toFixed(Number(row.value || 0) < total * 0.001 ? 3 : 1)
        return `${shortName} ${Number(row.value || 0).toLocaleString()}｜${percent}%`
      },
    },
    series: [
      {
        type: 'pie',
        radius: ['45%', '72%'],
        center: ['50%', '42%'],
        label: { color: '#f3fbff', formatter: '{b}\n{c}' },
        data: rows,
      },
    ],
  }
  const ref = useChart(option, [rows], (chart) => {
    chart.on('click', (params) => {
      const index = rows.findIndex((item) => item.name === params.name)
      if (index >= 0 && onSelect) onSelect(index, rows[index])
    })
  })
  return (
    <section className="side-panel">
      <PanelTitle title={title} />
      <div ref={ref} className="chart-small" />
    </section>
  )
}

function TimelineChart({ rows, activeIndex, onSelect }) {
  const option = {
    tooltip: { trigger: 'axis' },
    grid: { left: 42, right: 18, top: 20, bottom: 28 },
    xAxis: {
      type: 'category',
      data: rows.map((item) => item.date.slice(5)),
      axisLabel: { color: '#8dd8ff' },
      axisLine: { lineStyle: { color: '#2b6d9b' } },
    },
    yAxis: {
      type: 'value',
      axisLabel: { color: '#8dd8ff' },
      splitLine: { lineStyle: { color: 'rgba(124, 200, 239, 0.12)' } },
    },
    series: [
      {
        type: 'line',
        smooth: true,
        data: rows.map((item) => item.count),
        symbolSize: rows.map((_, idx) => (idx === activeIndex ? 10 : 6)),
        lineStyle: { color: '#33c2ff', width: 3 },
        itemStyle: { color: '#ffd166' },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(51, 194, 255, 0.35)' },
            { offset: 1, color: 'rgba(51, 194, 255, 0)' },
          ]),
        },
      },
    ],
  }
  const ref = useChart(option, [rows, activeIndex], (chart) => {
    chart.on('click', (params) => {
      const index = rows.findIndex((item) => item.date.slice(5) === params.name || item.date === params.name)
      if (index >= 0 && onSelect) onSelect(index, rows[index])
    })
  })
  return <div ref={ref} className="timeline-chart" />
}

function CommentFeed({ rows, activeRegion, activePlatform, activeLanguage, activeDate }) {
  const filtered = rows.filter((item) => {
    if (activeDate && item.date && item.date > activeDate) return false
    if (activeRegion && item.region_group !== activeRegion && item.region !== activeRegion) return false
    if (activePlatform && item.platform_group !== activePlatform && item.platform !== activePlatform) return false
    if (activeLanguage && !item.language.includes(activeLanguage.replace('（含原未标注语言）', '').replace('/文', ''))) return false
    return true
  })
  const visible = filtered.slice(-10).reverse()

  return (
    <section className="feed-panel">
      <PanelTitle title="历史原话动态滚动流" extra={activeDate ? `时间推进至 ${activeDate}` : ''} />
      <div className="feed-list">
        {visible.map((item, index) => (
          <article key={`${item.published_at}-${index}`} className="feed-item">
            <div className="feed-head">
              <span>{item.published_at ? item.published_at.slice(11, 16) : '--:--'}</span>
              <span>{item.platform}</span>
              <span>{item.region}</span>
            </div>
            <div className="feed-tag">{item.attitude}</div>
            <p>{item.text}</p>
          </article>
        ))}
      </div>
    </section>
  )
}

function findTopRegionIndexForPlatform(dashboard, platformName) {
  const counts = new Map()
  dashboard.feed.forEach((item) => {
    if (item.platform_group !== platformName && item.platform !== platformName) return
    if (!item.region_group) return
    counts.set(item.region_group, (counts.get(item.region_group) || 0) + 1)
  })
  const [regionName] = [...counts.entries()].sort((a, b) => b[1] - a[1])[0] || []
  return dashboard.map.regions.findIndex((item) => item.name === regionName)
}

export default function App() {
  const [dashboard, setDashboard] = useState(null)
  const [loading, setLoading] = useState(true)
  const [activeRegionIndex, setActiveRegionIndex] = useState(0)
  const [activePlatformIndex, setActivePlatformIndex] = useState(0)
  const [activeLanguageIndex, setActiveLanguageIndex] = useState(0)
  const [activeTimelineIndex, setActiveTimelineIndex] = useState(0)

  useEffect(() => {
    let mounted = true
    async function load() {
      setLoading(true)
      const res = await fetch('/api/dashboard')
      const data = await res.json()
      if (mounted) {
        setDashboard(data)
        setLoading(false)
      }
    }
    load()
    return () => {
      mounted = false
    }
  }, [])

  useEffect(() => {
    if (!dashboard?.map?.regions?.length) return
    const timer = setInterval(() => {
      setActiveRegionIndex((value) => (value + 1) % dashboard.map.regions.length)
    }, 4500)
    return () => clearInterval(timer)
  }, [dashboard])

  useEffect(() => {
    if (!dashboard?.platforms?.length) return
    const timer = setInterval(() => {
      setActivePlatformIndex((value) => (value + 1) % dashboard.platforms.length)
    }, 3800)
    return () => clearInterval(timer)
  }, [dashboard])

  useEffect(() => {
    if (!dashboard?.languages?.length) return
    const timer = setInterval(() => {
      setActiveLanguageIndex((value) => (value + 1) % dashboard.languages.length)
    }, 5200)
    return () => clearInterval(timer)
  }, [dashboard])

  useEffect(() => {
    if (!dashboard?.timeline?.length) return
    const timer = setInterval(() => {
      setActiveTimelineIndex((value) => (value + 1) % dashboard.timeline.length)
    }, 3000)
    return () => clearInterval(timer)
  }, [dashboard])

  if (loading || !dashboard) {
    return <div className="loading-screen">历史数据态势大屏加载中</div>
  }

  const activeRegion = dashboard.map.regions[activeRegionIndex]
  const activePlatform = dashboard.platforms[activePlatformIndex]
  const activeLanguage = dashboard.languages[activeLanguageIndex]
  const activeTimeline = dashboard.timeline[activeTimelineIndex]
  const platformAttitudes = (activePlatform?.attitudes || []).slice(0, 4)

  const selectRegion = (index) => {
    if (index < 0) return
    setActiveRegionIndex(index)
    const topPlatform = dashboard.map.regions[index]?.top_platforms?.[0]?.name
    const platformIndex = dashboard.platforms.findIndex((item) => item.name === topPlatform)
    if (platformIndex >= 0) setActivePlatformIndex(platformIndex)
  }

  const selectPlatform = (index) => {
    if (index < 0) return
    setActivePlatformIndex(index)
    const regionIndex = findTopRegionIndexForPlatform(dashboard, dashboard.platforms[index].name)
    if (regionIndex >= 0) setActiveRegionIndex(regionIndex)
  }

  return (
    <div className="screen">
      <header className="hero">
        <div>
          <div className="hero-kicker">民族相关网络舆情动态态势感知大屏</div>
          <h1>{dashboard.subtitle}</h1>
        </div>
        <div className="hero-meta">
          <div>历史时间范围</div>
          <strong>{dashboard.date_range.from} 至 {dashboard.date_range.to}</strong>
        </div>
      </header>

      <section className="metrics-grid">
        {dashboard.metrics.map((metric) => <MetricCard key={metric.label} metric={metric} />)}
      </section>

      <main className="main-grid">
        <div className="left-stack">
          <BarChart
            title="平台舆情量排名"
            rows={dashboard.platforms.slice(0, 7)}
            valueKey="total"
            activeName={activePlatform?.name}
            onSelect={(index) => selectPlatform(index)}
          />
          <RingChart
            title="语言分布"
            rows={dashboard.languages.map((item) => ({ name: item.name, value: item.value }))}
            onSelect={(index) => setActiveLanguageIndex(index)}
            showPercentLegend
          />
          <section className="focus-card">
            <PanelTitle title="轮播焦点" extra="平台｜语言" />
            <div className="focus-row">
              <span>当前平台</span>
              <strong>{activePlatform?.name}</strong>
            </div>
            <div className="focus-row">
              <span>平台占比</span>
              <strong>{((activePlatform?.share || 0) * 100).toFixed(1)}%</strong>
            </div>
            <div className="focus-row">
              <span>支持/非支持</span>
              <strong>{activePlatform?.support} / {activePlatform?.non_support}</strong>
            </div>
            <div className="focus-row">
              <span>来源/查看</span>
              <strong>{activePlatform?.source_count} / {activePlatform?.view_count}</strong>
            </div>
            <div className="focus-row">
              <span>当前语言</span>
              <strong>{activeLanguage?.name}</strong>
            </div>
            <div className="focus-row">
              <span>时间轴</span>
              <strong>{activeTimeline?.date}</strong>
            </div>
            <div className="mini-bar-list">
              {platformAttitudes.map((item) => (
                <div className="mini-bar" key={item.name}>
                  <span>{item.name}</span>
                  <i style={{ width: `${Math.max((item.value / Math.max(...platformAttitudes.map((row) => row.value), 1)) * 100, 2)}%` }} />
                  <strong>{item.value.toLocaleString()}</strong>
                </div>
              ))}
            </div>
          </section>
        </div>

        <MapPanel data={dashboard.map} activeRegionIndex={activeRegionIndex} onRegionSelect={selectRegion} />

        <div className="right-stack">
          <CommentFeed
            rows={dashboard.feed}
            activeRegion={activeRegion?.name}
            activePlatform={activePlatform?.name}
            activeLanguage={activeLanguage?.name}
            activeDate={activeTimeline?.date}
          />
        </div>
      </main>

      <section className="bottom-grid">
        <section className="bottom-panel">
          <PanelTitle title="总体态度结构" />
          <RingChart title="" rows={dashboard.overall_attitudes} />
        </section>
        <section className="bottom-panel">
          <BarChart title="非支持问题构成" rows={dashboard.non_support_breakdown} activeName={dashboard.non_support_breakdown[activeTimelineIndex % dashboard.non_support_breakdown.length]?.name} />
        </section>
        <section className="bottom-panel wide">
          <PanelTitle title="历史时间轴回放" extra={activeTimeline ? `${activeTimeline.top_region} ｜ ${activeTimeline.top_platform}` : ''} />
          <TimelineChart rows={dashboard.timeline} activeIndex={activeTimelineIndex} onSelect={setActiveTimelineIndex} />
        </section>
      </section>
    </div>
  )
}
