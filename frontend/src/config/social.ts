/**
 * Social follow configuration — single source of truth.
 * QUANT PILOT never verifies follows and never locks features behind them.
 */

export const SOCIAL = {
  youtube: {
    url: 'https://www.youtube.com/@sumedhhkumar?sub_confirmation=1',
    label: '@sumedhhkumar',
  },
  instagram: {
    url: 'https://www.instagram.com/sumedhhkumar.ai/',
    appScheme: 'instagram://user?username=sumedhhkumar.ai',
    label: '@sumedhhkumar.ai',
  },
} as const;

export const OPEN_IN_NEW_TAB: Pick<Window, 'open'> = window;

export function openSocial(kind: 'youtube' | 'instagram') {
  if (kind === 'youtube') {
    window.open(SOCIAL.youtube.url, '_blank', 'noopener,noreferrer');
    return;
  }
  // On mobile the app scheme may work; web URL is the documented fallback.
  const ua = navigator.userAgent.toLowerCase();
  const isMobile = /android|iphone|ipad|ipod/.test(ua);
  if (isMobile) {
    window.location.href = SOCIAL.instagram.appScheme;
    // Fallback to web after a short grace period if the scheme didn't take over.
    window.setTimeout(() => window.open(SOCIAL.instagram.url, '_blank', 'noopener,noreferrer'), 800);
    return;
  }
  window.open(SOCIAL.instagram.url, '_blank', 'noopener,noreferrer');
}