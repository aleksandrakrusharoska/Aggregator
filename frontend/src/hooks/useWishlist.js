import { useState, useEffect, useCallback } from 'react'

const KEY = 'wishlist_ads'

function load() {
  try { return JSON.parse(localStorage.getItem(KEY) || '[]') } catch { return [] }
}

function save(ads) {
  localStorage.setItem(KEY, JSON.stringify(ads))
}

export function useWishlist() {
  const [wishlist, setWishlist] = useState(load)

  useEffect(() => { save(wishlist) }, [wishlist])

  const toggle = useCallback(ad => {
    setWishlist(prev => {
      const exists = prev.some(a => a.ad_url === ad.ad_url)
      return exists ? prev.filter(a => a.ad_url !== ad.ad_url) : [ad, ...prev]
    })
  }, [])

  const isSaved = useCallback(
    ad_url => wishlist.some(a => a.ad_url === ad_url),
    [wishlist]
  )

  const clear = useCallback(() => setWishlist([]), [])

  return { wishlist, toggle, isSaved, clear }
}
