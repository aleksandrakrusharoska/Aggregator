import { useEffect, useState } from 'react'

const SOURCE_LABELS = { reklama5: 'Reklama5', pazar3: 'Pazar3' }
const CONDITION_MK = {
  new: 'Нов', like_new: 'Kako nov', used: 'Користен', for_parts: 'За делови',
}
const SELLER_TYPE_MK = { private: 'Физичко лице', business: 'Правно лице' }

export default function AdModal({ ad, onClose, isSaved, onWishlistToggle }) {
  const [imgIdx, setImgIdx] = useState(0)
  const images = Array.isArray(ad.images) ? ad.images : (ad.image_url ? [ad.image_url] : [])

  const prev = () => setImgIdx(i => (i - 1 + images.length) % images.length)
  const next = () => setImgIdx(i => (i + 1) % images.length)

  useEffect(() => {
    const onKey = e => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft'  && images.length > 1) prev()
      if (e.key === 'ArrowRight' && images.length > 1) next()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [onClose, images.length])

  const daysSinceScraped = (() => {
    const ref = ad.scraped_at || ad.posted_date
    if (!ref) return null
    return Math.floor((Date.now() - new Date(ref).getTime()) / 86_400_000)
  })()

  const specs = ad.specs && typeof ad.specs === 'object' ? ad.specs : {}
  const hasSpecs = Object.keys(specs).length > 0

  const isCheapAnomaly = ad.is_anomaly && ad.price_zscore < 0
  const isExpensiveAnomaly = ad.is_anomaly && ad.price_zscore > 0

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4"
      onClick={e => { if (e.target === e.currentTarget) onClose() }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/60 backdrop-blur-sm" onClick={onClose} />

      {/* Panel */}
      <div className="relative z-10 w-full sm:max-w-3xl max-h-[95dvh] bg-white dark:bg-slate-900 sm:rounded-2xl overflow-hidden flex flex-col shadow-2xl animate-slideUp">

        {/* Header */}
        <div className="flex items-start gap-3 p-5 pb-4 border-b border-slate-100 dark:border-slate-800 shrink-0">
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1 flex-wrap">
              <span className="text-[11px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900/30 text-violet-700 dark:text-violet-300">
                {SOURCE_LABELS[ad.source] || ad.source}
              </span>
              {ad.condition && (
                <span className="text-[11px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                  {CONDITION_MK[ad.condition] || ad.condition}
                </span>
              )}
              {ad.delivery_available && (
                <span className="text-[11px] font-semibold uppercase tracking-wide px-1.5 py-0.5 rounded bg-violet-100 dark:bg-violet-900/30 text-violet-600 dark:text-violet-300">
                  Достава
                </span>
              )}
            </div>
            <h2 className="text-lg font-semibold text-slate-900 dark:text-slate-100 leading-snug">
              {ad.title}
            </h2>
          </div>
          {onWishlistToggle && (
            <button
              onClick={() => onWishlistToggle(ad)}
              className={`shrink-0 rounded-lg p-2 transition-colors ${
                isSaved
                  ? 'text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20'
                  : 'text-slate-400 hover:text-red-400 hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
              aria-label={isSaved ? 'Отстрани од листа на желби' : 'Зачувај'}
            >
              <svg className="w-5 h-5" fill={isSaved ? 'currentColor' : 'none'} viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
              </svg>
            </button>
          )}
          <button
            onClick={onClose}
            className="shrink-0 rounded-lg p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
            aria-label="Затвори"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Anomaly banners */}
        {isCheapAnomaly && (
          <div className="shrink-0 flex items-center gap-3 px-5 py-2.5 bg-emerald-50 dark:bg-emerald-950/30 border-b border-emerald-100 dark:border-emerald-900/30">
            <svg className="w-4 h-4 text-emerald-600 dark:text-emerald-400 shrink-0" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M12.395 2.553a1 1 0 00-1.45-.385c-.345.23-.614.558-.822.88-.214.33-.403.713-.57 1.116-.334.804-.614 1.768-.84 2.734a31.365 31.365 0 00-.613 3.58 2.64 2.64 0 01-.945-1.067c-.328-.68-.398-1.534-.398-2.654A1 1 0 005.05 6.05 6.981 6.981 0 003 11a7 7 0 1011.95-4.95c-.592-.591-.98-.985-1.348-1.467-.363-.476-.724-1.063-1.207-2.03zM12.12 15.12A3 3 0 017 13s.879.5 2.5.5c0-1 .5-4 1.25-4.5.5 1 .786 1.293 1.371 1.879A2.99 2.99 0 0113 13a2.99 2.99 0 01-.879 2.121z" clipRule="evenodd" />
            </svg>
            <span className="text-sm font-medium text-emerald-700 dark:text-emerald-300">Детектирана добра цена</span>
            <span className="text-xs text-emerald-600/70 dark:text-emerald-400/70">
              {Math.abs(ad.price_zscore).toFixed(1)}σ под просекот за сличен производ
            </span>
          </div>
        )}
        {isExpensiveAnomaly && (
          <div className="shrink-0 flex items-center gap-3 px-5 py-2.5 bg-amber-50 dark:bg-amber-950/30 border-b border-amber-100 dark:border-amber-900/30">
            <svg className="w-4 h-4 text-amber-600 dark:text-amber-400 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <span className="text-sm font-medium text-amber-700 dark:text-amber-300">Висока цена</span>
            <span className="text-xs text-amber-600/70 dark:text-amber-400/70">
              {Math.abs(ad.price_zscore).toFixed(1)}σ над просекот за сличен производ
            </span>
          </div>
        )}

        {/* Scrollable body */}
        <div className="flex-1 overflow-y-auto">
          <div className="grid sm:grid-cols-2 gap-0">

            {/* Left: image + price */}
            <div className="p-5 space-y-4">
              {/* Gallery */}
              {images.length > 0 ? (
                <div className="space-y-2">
                  <div className="aspect-[4/3] bg-slate-100 dark:bg-slate-800 rounded-xl overflow-hidden relative group/img">
                    <img
                      src={images[imgIdx]}
                      alt={ad.title}
                      className="w-full h-full object-contain"
                      onError={e => { e.target.style.display = 'none' }}
                    />
                    {images.length > 1 && (
                      <>
                        <button
                          onClick={prev}
                          className="absolute left-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/40 hover:bg-black/60 text-white flex items-center justify-center opacity-0 group-hover/img:opacity-100 transition-opacity backdrop-blur-sm"
                          aria-label="Претходна слика"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
                          </svg>
                        </button>
                        <button
                          onClick={next}
                          className="absolute right-2 top-1/2 -translate-y-1/2 w-8 h-8 rounded-full bg-black/40 hover:bg-black/60 text-white flex items-center justify-center opacity-0 group-hover/img:opacity-100 transition-opacity backdrop-blur-sm"
                          aria-label="Следна слика"
                        >
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
                          </svg>
                        </button>
                        <div className="absolute bottom-2 left-1/2 -translate-x-1/2 flex gap-1">
                          {images.map((_, i) => (
                            <button
                              key={i}
                              onClick={() => setImgIdx(i)}
                              className={`w-1.5 h-1.5 rounded-full transition-all ${i === imgIdx ? 'bg-white w-3' : 'bg-white/50'}`}
                            />
                          ))}
                        </div>
                      </>
                    )}
                  </div>
                  {images.length > 1 && (
                    <div className="flex gap-1.5 overflow-x-auto pb-1">
                      {images.map((src, i) => (
                        <button
                          key={i}
                          onClick={() => setImgIdx(i)}
                          className={`shrink-0 w-14 h-14 rounded-lg overflow-hidden border-2 transition-colors ${
                            i === imgIdx ? 'border-violet-500' : 'border-transparent hover:border-slate-300 dark:hover:border-slate-600'
                          }`}
                        >
                          <img src={src} alt="" className="w-full h-full object-contain" onError={e => { e.target.style.display = 'none' }} />
                        </button>
                      ))}
                    </div>
                  )}
                </div>
              ) : (
                <div className="aspect-[4/3] bg-slate-100 dark:bg-slate-800 rounded-xl flex items-center justify-center">
                  <svg className="w-16 h-16 text-slate-300 dark:text-slate-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                </div>
              )}

              {/* Price */}
              <div className="flex items-baseline gap-2 flex-wrap">
                {ad.price_eur ? (
                  <span className="text-2xl font-bold text-violet-600 dark:text-violet-400 font-mono">
                    {Number(ad.price_eur).toLocaleString('mk-MK')} €
                  </span>
                ) : (
                  <span className="text-lg text-slate-400 dark:text-slate-500">По договор</span>
                )}
                {ad.price_mkd && (
                  <span className="text-sm text-slate-400 dark:text-slate-500 font-mono">
                    ≈ {Number(ad.price_mkd).toLocaleString('mk-MK')} МКД
                  </span>
                )}
              </div>

              {/* Meta */}
              <dl className="space-y-1.5 text-sm">
                {ad.location && (
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                    </svg>
                    {ad.location}
                  </div>
                )}
                {ad.seller_name && (
                  <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400">
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                    </svg>
                    <span>{ad.seller_name}</span>
                    {ad.seller_type && (
                      <span className="text-[11px] text-slate-400 dark:text-slate-500">
                        ({SELLER_TYPE_MK[ad.seller_type] || ad.seller_type})
                      </span>
                    )}
                  </div>
                )}
                {ad.delivery_available && (
                  <div className="flex items-center gap-2 text-emerald-600 dark:text-emerald-400">
                    <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                    </svg>
                    Достава можна
                  </div>
                )}
                {(ad.posted_date || ad.scraped_at) && (
                  <div className="text-slate-400 dark:text-slate-500 font-mono text-xs">
                    Огласено: {new Date(ad.posted_date || ad.scraped_at).toLocaleDateString('mk-MK')}
                  </div>
                )}
              </dl>

              {/* Cluster tag */}
              {ad.cluster_label && (
                <div className="flex items-center gap-2 text-xs text-slate-400 dark:text-slate-500 bg-slate-50 dark:bg-slate-800/60 rounded-lg px-3 py-2 border border-slate-100 dark:border-slate-800">
                  <svg className="w-3.5 h-3.5 shrink-0 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7 20l4-16m2 16l4-16M6 9h14M4 15h14" />
                  </svg>
                  <span className="font-mono truncate">{ad.cluster_label}</span>
                </div>
              )}

              {/* Stale warning */}
              {daysSinceScraped !== null && daysSinceScraped > 30 && (
                <div className="flex items-start gap-2 text-xs text-amber-600 dark:text-amber-400 bg-amber-50 dark:bg-amber-900/20 rounded-lg px-3 py-2 border border-amber-100 dark:border-amber-800">
                  <svg className="w-3.5 h-3.5 shrink-0 mt-0.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <span>Овој оглас е објавен пред повеќе од {daysSinceScraped} дена. Можно е производот да е веќе продаден.</span>
                </div>
              )}

              {/* Link */}
              {ad.ad_url && (
                <a
                  href={ad.ad_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-violet-600 hover:bg-violet-700 text-white text-sm font-medium transition-colors"
                >
                  Погледни оглас
                  <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                  </svg>
                </a>
              )}
            </div>

            {/* Right: specs + description */}
            <div className="p-5 space-y-4 border-t sm:border-t-0 sm:border-l border-slate-100 dark:border-slate-800">

              {/* Specs */}
              {hasSpecs && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">
                    Спецификации
                  </h4>
                  <dl className="space-y-0">
                    {Object.entries(specs).map(([k, v]) => (
                      <div key={k} className="flex gap-2 text-sm py-1.5 border-b border-slate-50 dark:border-slate-800 last:border-0">
                        <dt className="text-slate-500 dark:text-slate-500 shrink-0 w-2/5">{k}</dt>
                        <dd className="text-slate-800 dark:text-slate-200 font-medium min-w-0 break-words">{v}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              {/* Description */}
              {ad.description && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">
                    Опис
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed whitespace-pre-line line-clamp-[12]">
                    {ad.description}
                  </p>
                </div>
              )}

              {/* Seller notes */}
              {ad.seller_notes && (
                <div>
                  <h4 className="text-xs font-semibold uppercase tracking-widest text-slate-400 dark:text-slate-500 mb-2">
                    Белешки
                  </h4>
                  <p className="text-sm text-slate-600 dark:text-slate-400 leading-relaxed italic">
                    {ad.seller_notes}
                  </p>
                </div>
              )}

              {!hasSpecs && !ad.description && !ad.seller_notes && (
                <p className="text-sm text-slate-400 dark:text-slate-600 italic">
                  Нема дополнителни информации
                </p>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
