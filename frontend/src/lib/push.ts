import { apiClient } from "../api/client";

export interface NotificationConfig {
  vapid_public_key: string;
  push_available: boolean;
  email_available: boolean;
}

export type PushState =
  | "unsupported" // this browser cannot receive push at all
  | "needs-install" // iPhone/iPad: only works once added to the home screen
  | "denied" // the student blocked notifications for this site
  | "off"
  | "on";

export function isIos(): boolean {
  return /iphone|ipad|ipod/i.test(navigator.userAgent) ||
    (navigator.platform === "MacIntel" && navigator.maxTouchPoints > 1);
}

function isStandalone(): boolean {
  return (
    window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true
  );
}

export async function registerServiceWorker(): Promise<ServiceWorkerRegistration | null> {
  if (!("serviceWorker" in navigator)) return null;
  try {
    return await navigator.serviceWorker.register("/sw.js", { scope: "/" });
  } catch {
    return null;
  }
}

export async function getNotificationConfig(): Promise<NotificationConfig> {
  const { data } = await apiClient.get<NotificationConfig>("/notifications/config");
  return data;
}

export async function pushState(): Promise<PushState> {
  if (!("serviceWorker" in navigator) || !("PushManager" in window) || !("Notification" in window)) {
    return isIos() && !isStandalone() ? "needs-install" : "unsupported";
  }
  if (Notification.permission === "denied") return "denied";
  const registration = await navigator.serviceWorker.getRegistration("/");
  const subscription = await registration?.pushManager.getSubscription();
  return subscription ? "on" : "off";
}

function urlBase64ToBuffer(base64: string): ArrayBuffer {
  const padding = "=".repeat((4 - (base64.length % 4)) % 4);
  const raw = atob((base64 + padding).replace(/-/g, "+").replace(/_/g, "/"));
  return Uint8Array.from(raw, (char) => char.charCodeAt(0)).buffer;
}

/** Ask permission, subscribe this device, and register it with the API. */
export async function enablePush(vapidPublicKey: string): Promise<PushState> {
  const permission = await Notification.requestPermission();
  if (permission !== "granted") return permission === "denied" ? "denied" : "off";

  const registration = (await registerServiceWorker()) ?? (await navigator.serviceWorker.ready);
  const subscription =
    (await registration.pushManager.getSubscription()) ??
    (await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: urlBase64ToBuffer(vapidPublicKey),
    }));

  const json = subscription.toJSON();
  await apiClient.post("/notifications/subscriptions", {
    endpoint: subscription.endpoint,
    p256dh: json.keys?.p256dh,
    auth: json.keys?.auth,
  });
  return "on";
}

export async function disablePush(): Promise<PushState> {
  const registration = await navigator.serviceWorker.getRegistration("/");
  const subscription = await registration?.pushManager.getSubscription();
  if (subscription) {
    await apiClient
      .post("/notifications/subscriptions/remove", { endpoint: subscription.endpoint })
      .catch(() => undefined);
    await subscription.unsubscribe();
  }
  return "off";
}

export async function sendTestNotification(): Promise<{ push: number; email: boolean }> {
  const { data } = await apiClient.post<{ push: number; email: boolean }>("/notifications/test");
  return data;
}
