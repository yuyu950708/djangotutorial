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
      // 僅 blob: 預覽網址需要 revoke；data: URL 不必釋放
      if (this.pendingPreview && String(this.pendingPreview).startsWith("blob:")) {
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

    /**
     * 用 FileReader 把檔案讀成 Data URL（內含 Base64）。
     * 後端會解析 `data:<mime>;base64,<payload>`，不要只傳 blob: 或 /media/ 路徑。
     */
    fileToDataURL(file) {
      return new Promise((resolve, reject) => {
        const fr = new FileReader();
        fr.onload = () => resolve(fr.result);
        fr.onerror = () => reject(fr.error || new Error("讀取圖片失敗"));
        fr.readAsDataURL(file);
      });
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

      // 若有檔案：讀成 Base64（Data URL），供後端解碼後送進模型；絕不把 blob URL 當成圖片內容傳給 API
      let imageBase64 = null;
      let displayImage = previewCopy || null;
      if (fileCopy) {
        try {
          imageBase64 = await this.fileToDataURL(fileCopy);
          displayImage = imageBase64;
        } catch (e) {
          this.sending = false;
          this.messages.push({
            role: "assistant",
            text: "抱歉：無法讀取圖片，請換一張再試。",
          });
          queueMicrotask(() => this.scrollToBottom());
          return;
        }
      }

      this.messages.push({
        role: "user",
        text: text || (fileCopy ? "（已上傳圖片）" : ""),
        image: displayImage || null,
      });
      this.input = "";
      this.pendingFile = null;
      this.pendingPreview = null;
      const fileInput = document.getElementById("food-ai-file");
      if (fileInput) fileInput.value = "";

      const token = this.getCookie("csrftoken");
      // JSON 傳送：history 為陣列；圖片為完整 Data URL（後端會去掉 data: 前綴只保留 raw base64 給 Gemini）
      const body = {
        message: text || (fileCopy ? "（請看這張圖）" : ""),
        history: this.historyForApi(),
      };
      if (imageBase64) {
        body.image_base64 = imageBase64;
      }

      try {
        const res = await fetch(endpoint, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            ...(token ? { "X-CSRFToken": token } : {}),
          },
          body: JSON.stringify(body),
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
