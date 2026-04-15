/**
 * 等等吃啥 · AI 美食助理（前端）
 */
document.addEventListener("alpine:init", () => {
  Alpine.data("foodAiAssistant", () => ({
    open: false,
    messages: [],
    input: "",
    sending: false,
    pendingFile: null,
    pendingPreview: null,
    quickPrompts: ["今晚吃什麼？", "兩人聚餐預算 800 怎麼點？", "少油少鹽可以怎麼吃？"],

    init() {
      this.resetWelcome();
    },

    resetWelcome() {
      this.messages = [
        {
          role: "assistant",
          text: "嗨，我是等等吃啥的美食助理。可以問我聚餐、口味、預算，或上傳食物照片一起討論。",
          isWelcome: true,
        },
      ];
    },

    toggle() {
      this.open = !this.open;
      if (this.open) {
        queueMicrotask(() => this.scrollToBottom());
      }
    },

    clearConversation() {
      if (this.sending) return;
      this.resetWelcome();
      this.clearImage();
      this.input = "";
      queueMicrotask(() => this.scrollToBottom());
    },

    useQuick(text) {
      this.input = text;
      queueMicrotask(() => {
        const ta = document.querySelector("[data-food-ai-input]");
        if (ta) ta.focus();
      });
    },

    clearImage() {
      if (this.pendingPreview) {
        URL.revokeObjectURL(this.pendingPreview);
      }
      this.pendingFile = null;
      this.pendingPreview = null;
      const el = document.getElementById("food-ai-file");
      if (el) el.value = "";
    },

    pickImage(event) {
      const f = event.target.files && event.target.files[0];
      if (!f) return;
      if (f.size > 5 * 1024 * 1024) {
        window.alert("圖片請小於 5MB");
        event.target.value = "";
        return;
      }
      this.clearImage();
      this.pendingFile = f;
      this.pendingPreview = URL.createObjectURL(f);
    },

    getCookie(name) {
      if (!document.cookie) return null;
      const parts = document.cookie.split(";");
      for (let i = 0; i < parts.length; i++) {
        const c = parts[i].trim();
        if (c.startsWith(name + "=")) {
          return decodeURIComponent(c.slice(name.length + 1));
        }
      }
      return null;
    },

    historyForApi() {
      return this.messages
        .filter((m) => !m.isWelcome && (m.role === "user" || m.role === "assistant"))
        .map((m) => ({
          role: m.role,
          content: (m.text || "").slice(0, 4000),
        }))
        .filter((m) => m.content.length > 0);
    },

    scrollToBottom() {
      const el = document.getElementById("food-ai-scroll");
      if (el) el.scrollTop = el.scrollHeight;
    },

    async sendMessage() {
      if (this.sending) return;
      const text = (this.input || "").trim();
      if (!text && !this.pendingFile) return;

      const endpoint = document.body.getAttribute("data-ai-chat-url");
      if (!endpoint) {
        this.messages.push({
          role: "assistant",
          text: "請先登入後再使用 AI 助理。",
        });
        return;
      }

      this.sending = true;
      const fileCopy = this.pendingFile;
      const previewCopy = this.pendingPreview;

      const historyJson = JSON.stringify(this.historyForApi());

      this.messages.push({
        role: "user",
        text: text || (fileCopy ? "（已上傳圖片）" : ""),
        image: previewCopy || null,
      });
      this.input = "";
      this.pendingFile = null;
      this.pendingPreview = null;
      const fileInput = document.getElementById("food-ai-file");
      if (fileInput) fileInput.value = "";

      const fd = new FormData();
      fd.append("message", text || (fileCopy ? "（請看這張圖）" : ""));
      fd.append("history", historyJson);
      if (fileCopy) fd.append("image", fileCopy);

      const token = this.getCookie("csrftoken");

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: token ? { "X-CSRFToken": token } : {},
          body: fd,
          credentials: "same-origin",
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok) {
          throw new Error(data.error || res.statusText || "請求失敗");
        }
        this.messages.push({
          role: "assistant",
          text: data.reply || "（沒有回覆內容）",
        });
      } catch (e) {
        this.messages.push({
          role: "assistant",
          text: "抱歉：" + (e.message || "請稍後再試"),
        });
      } finally {
        this.sending = false;
        queueMicrotask(() => this.scrollToBottom());
      }
    },
  }));
});
