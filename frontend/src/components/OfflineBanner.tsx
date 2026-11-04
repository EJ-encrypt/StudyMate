import { WifiOff } from "lucide-react";
import { useEffect, useRef } from "react";

import { useOnline } from "../lib/network";
import { toast } from "../lib/toast";

/** A strip across the top while the device is offline, and a note when it is back. */
export default function OfflineBanner() {
  const online = useOnline();
  const wasOffline = useRef(false);

  useEffect(() => {
    if (!online) wasOffline.current = true;
    else if (wasOffline.current) {
      wasOffline.current = false;
      toast("You're back online.");
    }
  }, [online]);

  if (online) return null;
  return (
    <div role="status" className="sticky top-0 z-30 flex items-center justify-center gap-2 bg-red-600 px-4 py-2 text-center text-sm font-semibold text-white">
      <WifiOff className="h-4 w-4 shrink-0" aria-hidden />
      You're offline. Nothing you do now will be saved until you reconnect.
    </div>
  );
}
