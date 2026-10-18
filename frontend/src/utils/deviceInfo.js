// src/utils/deviceInfo.js
//
// Client-side display helpers for active sessions and device information.
// Note: Core security and device parsing are strictly handled server-side from
// the request User-Agent header; these helpers provide friendly formatting for the UI.

export const DEVICE_ICONS = {
  desktop: "🖥️",
  mobile: "📱",
  tablet: "📟",
  unknown: "💻",
};

export const getDeviceIcon = (deviceType) => {
  return DEVICE_ICONS[deviceType?.toLowerCase()] || DEVICE_ICONS.unknown;
};

export const formatSessionDate = (dateString) => {
  if (!dateString) return "—";
  try {
    return new Date(dateString).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });
  } catch {
    return dateString;
  }
};

export const getClientDisplayHints = () => {
  if (typeof window === "undefined" || typeof navigator === "undefined") {
    return {};
  }
  return {
    language: navigator.language || "en",
    platform: navigator.userAgentData?.platform || navigator.platform || "Unknown",
    isTouchDevice: "ontouchstart" in window || (navigator.maxTouchPoints || 0) > 0,
  };
};
