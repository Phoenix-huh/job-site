"use client";

import { useEffect, useState } from "react";
import { Sparkles, X } from "lucide-react";

export function NotificationToast() {
  const [notifications, setNotifications] = useState([]);

  useEffect(() => {
    const eventSource = new EventSource("http://localhost:8000/api/notifications/stream");

    eventSource.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === "new_job") {
        const id = Date.now();
        setNotifications((prev) => [...prev, { id, message: `New job added: ${data.title}` }]);
        
        // Auto remove after 5 seconds
        setTimeout(() => {
          setNotifications((prev) => prev.filter((n) => n.id !== id));
        }, 5000);
      }
    };

    return () => {
      eventSource.close();
    };
  }, []);

  const removeNotification = (id) => {
    setNotifications((prev) => prev.filter((n) => n.id !== id));
  };

  if (notifications.length === 0) return null;

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {notifications.map((notification) => (
        <div key={notification.id} className="bg-background border border-primary/30 shadow-lg shadow-primary/10 rounded-lg p-4 flex items-start gap-4 min-w-[300px] animate-in slide-in-from-bottom-5">
          <div className="bg-primary/10 p-2 rounded-full text-primary shrink-0">
            <Sparkles className="size-4" />
          </div>
          <div className="flex-1">
            <h4 className="text-sm border-b border-border/50 pb-1 font-semibold text-foreground">Alert</h4>
            <p className="text-sm text-foreground/80 mt-1">{notification.message}</p>
          </div>
          <button 
            onClick={() => removeNotification(notification.id)}
            className="text-foreground/50 hover:text-foreground transition-colors"
          >
            <X className="size-4" />
          </button>
        </div>
      ))}
    </div>
  );
}
