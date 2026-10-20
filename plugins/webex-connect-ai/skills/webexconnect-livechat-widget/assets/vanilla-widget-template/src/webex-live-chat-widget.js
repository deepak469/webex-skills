(function () {
  const config = window.WEBEX_CONNECT_WIDGET_CONFIG || {};
  const root = document.getElementById("webex-live-chat");
  if (!root) return;

  const launcher = root.querySelector(".wc-launcher");
  const panel = root.querySelector(".wc-panel");
  const closeButton = root.querySelector(".wc-close");
  const expandButton = root.querySelector("[data-expand]");
  const status = root.querySelector("[data-status]");
  const alertBox = root.querySelector("[data-alert]");
  const loginView = root.querySelector("[data-login-view]");
  const loginForm = root.querySelector("[data-login-form]");
  const loginUserId = root.querySelector("[data-login-user-id]");
  const loginCustomerId = root.querySelector("[data-login-customer-id]");
  const loginDeviceId = root.querySelector("[data-login-device-id]");
  const loginError = root.querySelector("[data-login-error]");
  const loginSubmit = root.querySelector("[data-login-submit]");
  const threadList = root.querySelector("[data-threads]");
  const threadEmpty = root.querySelector("[data-thread-empty]");
  const newThreadButton = root.querySelector("[data-new-thread]");
  const refreshThreadsButton = root.querySelector("[data-refresh-threads]");
  const workspace = root.querySelector(".wc-workspace");
  const conversation = root.querySelector("[data-conversation]");
  const conversationTitle = root.querySelector("[data-thread-title]");
  const conversationStatus = root.querySelector("[data-thread-status]");
  const conversationId = root.querySelector("[data-thread-id]");
  const closeThreadButton = root.querySelector("[data-close-thread]");
  const reopenThreadButton = root.querySelector("[data-reopen-thread]");
  const threadLocked = root.querySelector("[data-thread-locked]");
  const backButton = root.querySelector("[data-back-to-threads]");
  const list = root.querySelector("[data-messages]");
  const loading = root.querySelector("[data-loading]");
  const typing = root.querySelector("[data-typing]");
  const form = root.querySelector("[data-composer]");
  const input = root.querySelector("[data-input]");
  const emojiButton = root.querySelector("[data-emoji]");
  const sendButton = root.querySelector("[data-send]");
  const profileName = root.querySelector("[data-profile-name]");
  const profileSubtitle = root.querySelector("[data-profile-subtitle]");
  const profileAvatar = root.querySelector("[data-profile-avatar]");
  const titleModal = root.querySelector("[data-title-modal]");
  const titleForm = root.querySelector("[data-title-form]");
  const titleInput = root.querySelector("[data-title-input]");
  const titleError = root.querySelector("[data-title-error]");
  const titleCancelButtons = root.querySelectorAll("[data-title-cancel]");
  const titleSubmit = root.querySelector("[data-title-submit]");
  const settingsModal = root.querySelector("[data-settings-modal]");
  const settingsValues = root.querySelector("[data-settings-values]");
  const settingsOpen = root.querySelector("[data-settings-open]");
  const settingsClose = root.querySelector("[data-settings-close]");
  const requestPush = root.querySelector("[data-request-push]");
  const switchUserButton = root.querySelector("[data-switch-user]");
  const logoutButton = root.querySelector("[data-logout]");

  function hashIdentity(value) {
    let hash = 0;
    for (let index = 0; index < value.length; index += 1) {
      hash = ((hash << 5) - hash) + value.charCodeAt(index);
      hash |= 0;
    }
    return Math.abs(hash).toString(36);
  }

  const pageSize = Number(config.threadPageSize || 50);
  const storageKeyBase = config.storageKey || "webex-connect-selected-thread";
  const registrationStorageKey = config.registrationStorageKey || "webex-connect-registration-identity";
  let messaging = null;
  let threads = [];
  let currentThread = null;
  let currentMessages = [];
  let currentMessageKeys = new Set();
  let connected = false;
  let isCreatingThread = false;
  let lastConnectionStatus = "Starting";
  let isExpanded = false;
  let isInitialized = false;

  function setStatus(text) {
    if (status) status.textContent = text;
  }

  function showAlert(text) {
    if (!alertBox) return;
    alertBox.textContent = text || "";
    alertBox.hidden = !text;
  }

  function showLoginError(text) {
    if (!loginError) return;
    loginError.textContent = text || "";
    loginError.hidden = !text;
  }

  function setLoading(value) {
    if (loading) loading.hidden = !value;
  }

  function readStorage(key) {
    try {
      return localStorage.getItem(key);
    } catch {
      return null;
    }
  }

  function writeStorage(key, value) {
    try {
      localStorage.setItem(key, value);
    } catch {
      // Storage can be unavailable in privacy-restricted browser contexts.
    }
  }

  function removeStorage(key) {
    try {
      localStorage.removeItem(key);
    } catch {
      // Storage can be unavailable in privacy-restricted browser contexts.
    }
  }

  function getStorageKey() {
    const identityScope = JSON.stringify({
      userId: config.userId || "guest",
      customerId: config.customerId || "",
      appId: currentApplicationId()
    });
    return `${storageKeyBase}:${hashIdentity(identityScope)}`;
  }

  function escapeText(value) {
    return String(value == null ? "" : value).replace(/[&<>"']/g, (char) => ({
      "&": "&amp;",
      "<": "&lt;",
      ">": "&gt;",
      '"': "&quot;",
      "'": "&#039;"
    }[char]));
  }

  function readValue(value, ...names) {
    for (const name of names) {
      try {
        if (value && typeof value[name] === "function") return value[name]();
        if (value && value[name] !== undefined) return value[name];
      } catch {
        // SDK getters can throw when a property is not supported by a subtype.
      }
    }
    return undefined;
  }

  function asArray(value) {
    if (value == null) return [];
    if (Array.isArray(value)) return value;
    if (typeof value.length === "number" && typeof value !== "string") return Array.from(value);
    return [value];
  }

  function collection(value, names) {
    if (Array.isArray(value)) return value;
    for (const name of names) {
      const candidate = readValue(value, name);
      if (candidate != null) return asArray(candidate);
    }
    if (value && value.data && typeof value.data === "object") return collection(value.data, names);
    return [];
  }

  function firstText(value, names) {
    const result = readValue(value, ...names);
    if (result == null) return "";
    if (["string", "number", "boolean"].includes(typeof result)) return String(result);
    return firstText(result, ["getText", "getValue", "text", "value", "label", "title"]);
  }

  function lower(value) {
    return String(value == null ? "" : value).toLowerCase();
  }

  function threadId(thread) {
    if (!thread) return "";
    return String(readValue(thread, "getThreadId", "getThreadID", "getId", "threadId", "threadID", "id", "_id") || "");
  }

  function messageThread(message) {
    return readValue(message, "getThread", "thread") || null;
  }

  function messageThreadId(message) {
    return threadId(messageThread(message)) || String(readValue(message, "getThreadId", "getThreadID", "threadId", "threadID") || "");
  }

  function messageKey(message) {
    const transactionId = readValue(message, "getTransactionId", "transactionId");
    if (transactionId) return `transaction:${transactionId}`;
    const temporaryId = readValue(message, "getTemporaryId", "temporaryId");
    if (temporaryId) return `temporary:${temporaryId}`;
    const body = firstText(message, ["getMessage", "message"]);
    const created = readValue(message, "getSubmittedAt", "submittedAt", "getCreatedAt", "createdAt") || "";
    return `fallback:${messageThreadId(message)}:${created}:${body}`;
  }

  function threadTitle(thread) {
    return firstText(thread, ["getTitle", "title", "getName", "name"]) || "Untitled conversation";
  }

  function threadStatus(thread) {
    if (thread && thread.__wcStatus) return thread.__wcStatus;
    const text = lower(readValue(thread, "getStatus", "status"));
    if (text.includes("closed")) return "Closed";
    if (text.includes("announcement")) return "Announcement";
    return "Active";
  }

  function threadPreview(thread) {
    return thread.__wcPreview || firstText(thread, ["getLastMessage", "lastMessage", "getPreview", "preview"]) || "No messages yet";
  }

  function threadUnread(thread) {
    return Number(readValue(thread, "getUnreadCount", "unreadCount", "getUnreadMessagesCount", "unreadMessagesCount") || thread.__wcUnread || 0);
  }

  function formatTime(value) {
    if (!value) return "";
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    return date.toLocaleTimeString([], { hour: "numeric", minute: "2-digit" });
  }

  function threadTime(thread) {
    return readValue(thread, "getUpdatedAt", "updatedAt", "getLastMessageAt", "lastMessageAt", "getCreatedAt", "createdAt") || "";
  }

  function formatRelativeTime(value) {
    if (!value) return "";
    const date = value instanceof Date ? value : new Date(value);
    if (Number.isNaN(date.getTime())) return "";
    const seconds = Math.max(0, Math.floor((Date.now() - date.getTime()) / 1000));
    if (seconds < 60) return "Just now";
    const minutes = Math.floor(seconds / 60);
    if (minutes < 60) return `${minutes} ${minutes === 1 ? "min" : "mins"} ago`;
    const hours = Math.floor(minutes / 60);
    if (hours < 24) return `${hours} ${hours === 1 ? "hr" : "hrs"} ago`;
    const days = Math.floor(hours / 24);
    return `${days} ${days === 1 ? "day" : "days"} ago`;
  }

  function profileDisplayName() {
    return config.displayName || config.userId || "Webex Connect";
  }

  function initializeProfileHeader() {
    const name = profileDisplayName();
    if (profileName) profileName.textContent = name;
    if (profileSubtitle) profileSubtitle.textContent = config.profileSubtitle || "Live support";
    if (profileAvatar) profileAvatar.textContent = name.trim().charAt(0).toUpperCase() || "W";
  }

  function setLoginVisible(visible) {
    if (loginView) loginView.hidden = !visible;
    if (workspace) workspace.hidden = visible;
    if (settingsModal) settingsModal.hidden = true;
    if (titleModal) titleModal.hidden = true;
    if (visible) {
      currentThread = null;
      currentMessages = [];
      currentMessageKeys = new Set();
      setConversationVisible(false);
      setComposerEnabled(false);
    }
  }

  function setSettingsVisible(visible) {
    if (!settingsModal) return;
    settingsModal.hidden = !visible;
    if (workspace) workspace.hidden = visible;
    if (loginView) loginView.hidden = true;
    if (titleModal) titleModal.hidden = true;
    if (!visible) {
      if (currentThread) renderConversationHeader();
      else setConversationVisible(false);
    }
  }

  function setTitleVisible(visible) {
    if (!titleModal) return;
    titleModal.hidden = !visible;
    if (workspace) workspace.hidden = visible;
    if (loginView) loginView.hidden = true;
    if (settingsModal) settingsModal.hidden = true;
    if (!visible) {
      if (currentThread) renderConversationHeader();
      else setConversationVisible(false);
    }
  }

  function setExpanded(value) {
    isExpanded = Boolean(value);
    if (panel) panel.classList.toggle("is-expanded", isExpanded);
    if (root) root.classList.toggle("is-expanded", isExpanded);
    if (expandButton) {
      expandButton.textContent = isExpanded ? "↙" : "⛶";
      expandButton.setAttribute("aria-label", isExpanded ? "Restore widget size" : "Expand widget");
    }
  }

  function openTitleModal() {
    if (!titleModal || isCreatingThread) return;
    if (titleInput) titleInput.value = "";
    if (titleError) titleError.hidden = true;
    setTitleVisible(true);
    window.setTimeout(() => titleInput && titleInput.focus(), 0);
  }

  function closeTitleModal() {
    setTitleVisible(false);
  }

  function errorText(error) {
    return error instanceof Error ? error.message : String(error || "Unknown Webex Connect SDK error");
  }

  function callback(resolve, reject) {
    return {
      onSuccess: (value) => resolve(value),
      onFailure: (error) => reject(error)
    };
  }

  function call(target, method, args) {
    return new Promise((resolve, reject) => {
      if (!target || typeof target[method] !== "function") {
        reject(new Error(`Webex Connect SDK method ${method} is unavailable`));
        return;
      }
      try {
        target[method](...(args || []), callback(resolve, reject));
      } catch (error) {
        reject(error);
      }
    });
  }

  function setConversationVisible(value) {
    if (conversation) conversation.hidden = !value;
    if (threadList && threadList.parentElement) threadList.parentElement.classList.toggle("has-selection", value);
    if (backButton) backButton.hidden = !value;
  }

  function setComposerEnabled(enabled) {
    if (input) input.disabled = !enabled;
    if (emojiButton) emojiButton.disabled = !enabled;
    if (sendButton) sendButton.disabled = !enabled;
    if (input && !enabled) input.placeholder = "Select a conversation to start chatting";
    if (input && enabled) input.placeholder = "Write a message";
  }

  function renderThreadList() {
    if (!threadList) return;
    threadList.innerHTML = "";
    if (threadEmpty) threadEmpty.hidden = threads.length > 0;
    threads.forEach((thread) => {
      const id = threadId(thread);
      if (!id) return;
      const button = document.createElement("button");
      button.type = "button";
      button.className = `wc-thread${currentThread && threadId(currentThread) === id ? " is-selected" : ""}`;
      button.dataset.threadId = id;
      const main = document.createElement("span");
      main.className = "wc-thread-main";
      const title = document.createElement("strong");
      title.textContent = threadTitle(thread);
      const preview = document.createElement("span");
      preview.textContent = threadPreview(thread);
      main.append(title, preview);
      const meta = document.createElement("span");
      meta.className = "wc-thread-meta";
      const time = document.createElement("small");
      time.textContent = formatRelativeTime(threadTime(thread)) || threadStatus(thread);
      meta.appendChild(time);
      if (threadUnread(thread)) {
        const unread = document.createElement("b");
        unread.textContent = String(threadUnread(thread));
        meta.appendChild(unread);
      }
      button.append(main, meta);
      button.addEventListener("click", () => selectThread(thread));
      threadList.appendChild(button);
    });
  }

  function renderConversationHeader() {
    if (!currentThread) {
      setConversationVisible(false);
      return;
    }
    setConversationVisible(true);
    if (conversationTitle) conversationTitle.textContent = threadTitle(currentThread);
    if (conversationStatus) conversationStatus.textContent = threadStatus(currentThread);
    if (conversationId) conversationId.textContent = threadId(currentThread);
    const closed = threadStatus(currentThread) === "Closed";
    if (closeThreadButton) closeThreadButton.hidden = closed;
    if (reopenThreadButton) reopenThreadButton.hidden = !closed;
    if (threadLocked) threadLocked.hidden = !closed;
    setComposerEnabled(connected && !closed);
  }

  function mergeThread(thread) {
    if (!thread || !threadId(thread)) return;
    const id = threadId(thread);
    const existingIndex = threads.findIndex((item) => threadId(item) === id);
    if (existingIndex === -1) threads.unshift(thread);
    else threads[existingIndex] = Object.assign(threads[existingIndex], thread);
    renderThreadList();
  }

  function updateThreadFromMessage(message) {
    const id = messageThreadId(message);
    if (!id) return;
    let thread = threads.find((item) => threadId(item) === id);
    if (!thread) {
      thread = messageThread(message) || { id, title: "Untitled conversation" };
      mergeThread(thread);
    }
    thread.__wcPreview = firstText(message, ["getMessage", "message"]) || "New message";
    thread.__wcUnread = id === threadId(currentThread) ? 0 : threadUnread(thread) + 1;
    renderThreadList();
  }

  function normalizeMessages(result) {
    return collection(result, ["getMessages", "messages", "getItems", "items", "data"]);
  }

  function normalizeThreads(result) {
    return collection(result, ["getThreads", "threads", "getItems", "items", "data"]);
  }

  function mergeMessages(messages) {
    for (const message of messages || []) {
      const key = messageKey(message);
      if (currentMessageKeys.has(key)) continue;
      currentMessageKeys.add(key);
      currentMessages.push(message);
    }
    currentMessages.sort((a, b) => {
      const aTime = new Date(readValue(a, "getSubmittedAt", "submittedAt", "getCreatedAt", "createdAt") || 0).getTime();
      const bTime = new Date(readValue(b, "getSubmittedAt", "submittedAt", "getCreatedAt", "createdAt") || 0).getTime();
      if (!aTime || !bTime) return 0;
      return aTime - bTime;
    });
  }

  function isOutgoing(message) {
    const outgoing = readValue(message, "getOutgoing", "outgoing", "isOutgoing");
    if (typeof outgoing === "boolean") return outgoing;
    const sender = String(readValue(message, "getSenderId", "senderId", "getUserId", "userId") || "");
    return Boolean(config.userId && sender && sender === config.userId);
  }

  function messageType(message) {
    return lower(readValue(message, "getType", "type", "getMessageType", "messageType"));
  }

  function isReceiptOrLifecycle(type) {
    return ["readreceipt", "delivered", "clickedreceipt", "deleted", "updatethread", "reopenthread", "closethread"].some((name) => type.includes(name));
  }

  function findUrl(value) {
    const direct = readValue(value, "getUrl", "url", "getMediaUrl", "mediaUrl", "getDownloadUrl", "downloadUrl", "getImageUrl", "imageUrl", "getImageURL", "imageURL", "getImageURLs", "imageURLs", "getPreviewUrl", "previewUrl", "getUri", "uri");
    if (typeof direct === "string" && direct) return direct;
    if (Array.isArray(direct) && direct.length && typeof direct[0] === "string") return direct[0];
    const media = readValue(value, "getMedia", "media", "getAttachment", "attachment");
    if (media && media !== value) return findUrl(media);
    return "";
  }

  function findActionUrl(button) {
    const direct = readValue(button, "getActionURL", "actionURL", "getActionUrl", "actionUrl", "getUrl", "url");
    return typeof direct === "string" ? direct : "";
  }

  function findContentType(value) {
    return lower(readValue(value, "getContentType", "contentType", "getMimeType", "mimeType", "getType", "type"));
  }

  function createTextNode(text) {
    const paragraph = document.createElement("p");
    paragraph.className = "wc-rich-text";
    paragraph.textContent = text;
    return paragraph;
  }

  function addButton(button, sourceMessage, container) {
    const label = firstText(button, ["getTitle", "title", "getText", "text", "getLabel", "label", "name"]) || "Action";
    const url = findActionUrl(button);
    const action = document.createElement("button");
    action.type = "button";
    action.className = "wc-action";
    action.textContent = label;
    action.addEventListener("click", async () => {
      action.disabled = true;
      try {
        const transactionId = readValue(sourceMessage, "getTransactionId", "transactionId");
        if (url) {
          if (transactionId && messaging.sendClickedEvent) await call(messaging, "sendClickedEvent", [transactionId, button]);
          window.open(url, "_blank", "noopener,noreferrer");
          return;
        }
        await publishPostback(sourceMessage, button, label);
      } catch (error) {
        action.disabled = false;
        showAlert(errorText(error));
      }
    });
    container.appendChild(action);
  }

  async function publishPostback(sourceMessage, button, fallbackText) {
    let outbound = null;
    if (messaging && typeof messaging.createPostbackMessage === "function") {
      try { outbound = messaging.createPostbackMessage(sourceMessage, button); } catch { outbound = null; }
    }
    if (!outbound) {
      outbound = new IMI.ICMessage();
      outbound.setMessage(fallbackText || "Selected");
    }
    if (outbound.setThread) outbound.setThread(currentThread);
    if (outbound.setOutgoing) outbound.setOutgoing(true);
    await call(messaging, "publishMessage", [outbound]);
    appendOptimisticMessage(outbound);
  }

  function renderGenericTemplate(attachment, sourceMessage) {
    const elements = collection(attachment, ["getElements", "elements", "getCards", "cards", "items"]);
    if (!elements.length) return null;
    const carousel = document.createElement("div");
    carousel.className = "wc-carousel";
    elements.forEach((element) => {
      const card = document.createElement("article");
      card.className = "wc-card";
      const imageUrl = findUrl(readValue(element, "getImage", "image") || element);
      if (imageUrl) {
        const image = document.createElement("img");
        image.src = imageUrl;
        image.alt = firstText(element, ["getTitle", "title"]) || "";
        image.loading = "lazy";
        card.appendChild(image);
      }
      const title = firstText(element, ["getTitle", "title", "getName", "name"]);
      const subtitle = firstText(element, ["getSubtitle", "subtitle", "getDescription", "description", "getText", "text"]);
      if (title) card.appendChild(createTextNode(title));
      if (subtitle) {
        const detail = createTextNode(subtitle);
        detail.classList.add("wc-card-detail");
        card.appendChild(detail);
      }
      const buttons = collection(element, ["getButtons", "buttons", "getActions", "actions"]);
      if (buttons.length) {
        const actions = document.createElement("div");
        actions.className = "wc-actions";
        buttons.forEach((button) => addButton(button, sourceMessage, actions));
        card.appendChild(actions);
      }
      carousel.appendChild(card);
    });
    return carousel;
  }

  function fieldControl(field, index) {
    const name = firstText(field, ["getName", "name", "getId", "id", "getKey", "key"]) || `field_${index + 1}`;
    const label = firstText(field, ["getLabel", "label", "getTitle", "title", "getName", "name"]) || name;
    const type = lower(readValue(field, "getType", "type", "getFieldType", "fieldType"));
    const options = collection(field, ["getOptions", "options", "getChoices", "choices", "getValues", "values"]);
    let control;
    if (type.includes("dropdown") || type.includes("select")) {
      control = document.createElement("select");
      if (type.includes("multi")) control.multiple = true;
      options.forEach((option) => {
        const optionElement = document.createElement("option");
        optionElement.value = firstText(option, ["getValue", "value", "getId", "id"]) || firstText(option, ["getLabel", "label", "title"]);
        optionElement.textContent = firstText(option, ["getLabel", "label", "getTitle", "title", "value"]);
        control.appendChild(optionElement);
      });
    } else {
      control = document.createElement("input");
      control.type = type.includes("email") ? "email" : type.includes("integer") ? "number" : type.includes("decimal") ? "number" : type.includes("date") ? "date" : "text";
      if (control.type === "number" && type.includes("decimal")) control.step = "any";
    }
    control.name = name;
    control.dataset.wcFormControl = "true";
    if (readValue(field, "getRequired", "required", "isRequired", "getMandatory", "mandatory", "isMandatory")) control.required = true;
    const wrapper = document.createElement("label");
    wrapper.className = "wc-form-field";
    wrapper.appendChild(document.createTextNode(label));
    wrapper.appendChild(control);
    return wrapper;
  }

  function renderFormTemplate(attachment, sourceMessage) {
    const fields = collection(attachment, ["getFields", "fields", "getFormFields", "formFields"]);
    if (!fields.length) return null;
    const formElement = document.createElement("form");
    formElement.className = "wc-rich-form";
    const title = firstText(attachment, ["getTitle", "title", "getFormTitle", "formTitle"]);
    if (title) formElement.appendChild(createTextNode(title));
    fields.forEach((field, index) => formElement.appendChild(fieldControl(field, index)));
    const submit = document.createElement("button");
    submit.type = "submit";
    submit.className = "wc-action wc-form-submit";
    submit.textContent = firstText(attachment, ["getSubmitLabel", "submitLabel", "getButtonText", "buttonText"]) || "Submit";
    formElement.appendChild(submit);
    formElement.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (!formElement.reportValidity()) return;
      const values = {};
      formElement.querySelectorAll("[data-wc-form-control]").forEach((control) => {
        values[control.name] = control.multiple ? Array.from(control.selectedOptions).map((option) => option.value) : control.value;
      });
      submit.disabled = true;
      try {
        let outbound = null;
        if (messaging && typeof messaging.createPostbackMessage === "function") {
          try { outbound = messaging.createPostbackMessage(sourceMessage, submit); } catch { outbound = null; }
        }
        if (!outbound) outbound = new IMI.ICMessage();
        outbound.setMessage(JSON.stringify({ type: "FormResponse", values }));
        if (outbound.setThread) outbound.setThread(currentThread);
        if (outbound.setRelatedTransactionId) outbound.setRelatedTransactionId(readValue(sourceMessage, "getTransactionId", "transactionId"));
        await call(messaging, "publishMessage", [outbound]);
        formElement.querySelectorAll("input, select, button").forEach((control) => { control.disabled = true; });
        appendOptimisticMessage(outbound);
      } catch (error) {
        submit.disabled = false;
        showAlert(errorText(error));
      }
    });
    return formElement;
  }

  function renderQuickReplies(data, sourceMessage) {
    const buttons = collection(data, ["getQuickReplies", "quickReplies", "getButtons", "buttons", "getItems", "items"]);
    if (!buttons.length) return null;
    const actions = document.createElement("div");
    actions.className = "wc-quick-replies";
    buttons.forEach((button) => addButton(button, sourceMessage, actions));
    return actions;
  }

  function renderMedia(attachment) {
    const url = findUrl(attachment);
    if (!url) return null;
    const contentType = findContentType(attachment);
    const previewUrl = readValue(attachment, "getPreviewUrl", "previewUrl") || url;
    if (contentType.includes("image") || contentType === "image") {
      const image = document.createElement("img");
      image.className = "wc-media-image";
      image.src = previewUrl;
      image.alt = firstText(attachment, ["getFileName", "fileName", "name"]) || "Shared image";
      image.loading = "lazy";
      return image;
    }
    if (contentType.includes("audio")) {
      const audio = document.createElement("audio");
      audio.controls = true;
      audio.src = url;
      return audio;
    }
    if (contentType.includes("video")) {
      const video = document.createElement("video");
      video.controls = true;
      video.src = url;
      return video;
    }
    const link = document.createElement("a");
    link.className = "wc-file-link";
    link.href = url;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = firstText(attachment, ["getFileName", "fileName", "name"]) || "Open attachment";
    return link;
  }

  function renderLocation(attachment) {
    const latitude = readValue(attachment, "getLatitude", "latitude");
    const longitude = readValue(attachment, "getLongitude", "longitude");
    if (latitude == null || longitude == null) return null;
    const link = document.createElement("a");
    link.className = "wc-file-link";
    link.href = `https://www.google.com/maps?q=${encodeURIComponent(`${latitude},${longitude}`)}`;
    link.target = "_blank";
    link.rel = "noopener noreferrer";
    link.textContent = `View location (${latitude}, ${longitude})`;
    return link;
  }

  function richAttachmentKey(attachment) {
    const fields = collection(attachment, ["getFields", "fields", "getFormFields", "formFields"]);
    const elements = collection(attachment, ["getElements", "elements", "getCards", "cards", "items"]);
    const fieldNames = fields.map((field) => firstText(field, ["getName", "name", "getLabel", "label"])).join(",");
    const elementTitles = elements.map((element) => firstText(element, ["getTitle", "title", "getName", "name"])).join(",");
    return [
      findContentType(attachment),
      findUrl(attachment),
      firstText(attachment, ["getTitle", "title", "getFileName", "fileName", "name"]),
      fieldNames,
      elementTitles
    ].join("|");
  }

  function renderRichContent(message) {
    const fragment = document.createDocumentFragment();
    const attachments = [];
    const seenReferences = new Set();
    const seenSignatures = new Set();
    const addAttachment = (attachment) => {
      if (!attachment) return;
      if (typeof attachment === "object" && seenReferences.has(attachment)) return;
      const signature = richAttachmentKey(attachment);
      if (signature && seenSignatures.has(signature)) return;
      if (typeof attachment === "object") seenReferences.add(attachment);
      if (signature) seenSignatures.add(signature);
      attachments.push(attachment);
    };
    collection(message, ["getAttachments", "attachments"]).forEach(addAttachment);
    collection(message, ["getMedia", "media"]).forEach(addAttachment);
    const interactive = readValue(message, "getInteractiveData", "interactiveData");
    const quickReply = readValue(message, "getQuickReplyData", "quickReplyData");
    addAttachment(interactive);
    for (const attachment of attachments) {
      const fields = collection(attachment, ["getFields", "fields", "getFormFields", "formFields"]);
      const elements = collection(attachment, ["getElements", "elements", "getCards", "cards", "items"]);
      const location = renderLocation(attachment);
      const formTemplate = fields.length ? renderFormTemplate(attachment, message) : null;
      const carousel = elements.length ? renderGenericTemplate(attachment, message) : null;
      const media = renderMedia(attachment);
      if (formTemplate) fragment.appendChild(formTemplate);
      else if (carousel) fragment.appendChild(carousel);
      else if (location) fragment.appendChild(location);
      else if (media) fragment.appendChild(media);
    }
    const replies = quickReply ? renderQuickReplies(quickReply, message) : null;
    if (replies) fragment.appendChild(replies);
    return fragment;
  }

  function renderMessage(message) {
    const type = messageType(message);
    if (type.includes("typingstart") || type.includes("typingstop") || isReceiptOrLifecycle(type)) return null;
    const item = document.createElement("li");
    const outgoing = isOutgoing(message);
    item.className = `wc-message${outgoing ? " is-outgoing" : ""}`;
    item.dataset.messageKey = messageKey(message);
    const body = document.createElement("div");
    body.className = "wc-message-body";
    const text = firstText(message, ["getMessage", "message"]);
    if (text) body.appendChild(createTextNode(text));
    body.appendChild(renderRichContent(message));
    if (!body.childNodes.length) body.appendChild(createTextNode(type === "alert" ? "Service update" : "Message"));
    item.appendChild(body);
    const timestamp = readValue(message, "getSubmittedAt", "submittedAt", "getCreatedAt", "createdAt");
    const footer = document.createElement("span");
    footer.className = "wc-message-footer";
    footer.textContent = `${formatTime(timestamp)}${outgoing ? ` · ${message.__wcStatus || "Sent"}` : ""}`;
    item.appendChild(footer);
    return item;
  }

  function renderMessages() {
    if (!list) return;
    list.innerHTML = "";
    currentMessages.forEach((message) => {
      const item = renderMessage(message);
      if (item) list.appendChild(item);
    });
    list.scrollTop = list.scrollHeight;
  }

  function appendOptimisticMessage(message) {
    if (!message) return;
    message.__wcStatus = "Sent";
    const key = messageKey(message);
    if (!currentMessageKeys.has(key)) {
      currentMessageKeys.add(key);
      currentMessages.push(message);
    }
    updateThreadFromMessage(message);
    renderMessages();
  }

  async function loadThreadMessages(thread) {
    currentMessages = [];
    currentMessageKeys = new Set();
    renderMessages();
    setLoading(true);
    try {
      const result = await call(messaging, "fetchMessages", [threadId(thread), null, pageSize]);
      mergeMessages(normalizeMessages(result));
      renderMessages();
      currentMessages.forEach((message) => {
        const transactionId = readValue(message, "getTransactionId", "transactionId");
        if (transactionId && messaging.setMessageAsRead) call(messaging, "setMessageAsRead", [transactionId]).catch(() => {});
      });
    } catch (error) {
      showAlert(`Unable to load conversation history: ${errorText(error)}`);
    } finally {
      setLoading(false);
    }
  }

  async function selectThread(thread) {
    if (!thread || !threadId(thread) || !messaging) return;
    currentThread = thread;
    thread.__wcUnread = 0;
    writeStorage(getStorageKey(), threadId(thread));
    renderThreadList();
    renderConversationHeader();
    await loadThreadMessages(thread);
  }

  async function loadThreads() {
    const result = await call(messaging, "fetchThreads", [0, pageSize]);
    threads = normalizeThreads(result).filter((thread) => threadId(thread));
    renderThreadList();
    if (currentThread) {
      const refreshed = threads.find((thread) => threadId(thread) === threadId(currentThread));
      if (refreshed) {
        currentThread = refreshed;
        renderConversationHeader();
      } else {
        currentThread = null;
        setConversationVisible(false);
        setComposerEnabled(false);
      }
    } else {
      setConversationVisible(false);
      setComposerEnabled(false);
    }
  }

  async function createNewThread(title) {
    if (isCreatingThread || !messaging) return;
    isCreatingThread = true;
    if (newThreadButton) newThreadButton.disabled = true;
    showAlert("");
    try {
      const thread = new IMI.ICThread();
      thread.setTitle(title);
      thread.setStatus(IMI.ICThreadStatus.Active);
      thread.setType(IMI.ICThreadType.Conversation);
      const created = await call(messaging, "createThread", [thread]);
      const selected = created || thread;
      mergeThread(selected);
      await selectThread(selected);
    } catch (error) {
      showAlert(`Unable to create a new conversation: ${errorText(error)}`);
    } finally {
      isCreatingThread = false;
      if (newThreadButton) newThreadButton.disabled = false;
    }
  }

  async function closeCurrentThread() {
    if (!currentThread || !messaging || threadStatus(currentThread) === "Closed") return;
    if (closeThreadButton) closeThreadButton.disabled = true;
    try {
      const updated = await call(messaging, "closeThread", [currentThread]);
      currentThread = updated || currentThread;
      currentThread.__wcStatus = "Closed";
      mergeThread(currentThread);
      renderConversationHeader();
    } catch (error) {
      showAlert(`Unable to close this conversation: ${errorText(error)}`);
    } finally {
      if (closeThreadButton) closeThreadButton.disabled = false;
    }
  }

  async function reopenCurrentThread() {
    if (!currentThread || !messaging || threadStatus(currentThread) !== "Closed") return;
    if (reopenThreadButton) reopenThreadButton.disabled = true;
    try {
      if (IMI.ICThreadStatus && IMI.ICThreadStatus.Active && currentThread.setStatus) {
        currentThread.setStatus(IMI.ICThreadStatus.Active);
      }
      if (typeof messaging.reopenThread === "function") {
        const updated = await call(messaging, "reopenThread", [currentThread]);
        currentThread = updated || currentThread;
      } else {
        const updated = await call(messaging, "updateThread", [currentThread]);
        currentThread = updated || currentThread;
      }
      currentThread.__wcStatus = "Active";
      mergeThread(currentThread);
      renderConversationHeader();
    } catch (error) {
      showAlert(`Unable to reopen this conversation: ${errorText(error)}`);
    } finally {
      if (reopenThreadButton) reopenThreadButton.disabled = false;
    }
  }

  function appendSetting(label, value) {
    const row = document.createElement("div");
    row.className = "wc-setting-row";
    const name = document.createElement("span");
    name.className = "wc-setting-label";
    name.textContent = label;
    const detail = document.createElement("span");
    detail.className = "wc-setting-value";
    detail.textContent = value == null || value === "" ? "Not available" : String(value);
    row.append(name, detail);
    settingsValues.appendChild(row);
  }

  function refreshSettings() {
    if (!settingsValues) return;
    settingsValues.innerHTML = "";
    const asset = config.asset || {};
    const appId = config.appId || config.applicationId || asset.appId || "Not configured";
    const sdk = window.IMI || {};
    const sdkVersion = readValue(sdk, "getSDKVersion", "sdkVersion", "VERSION", "version")
      || readValue(messaging, "getSDKVersion", "sdkVersion")
      || readValue(sdk.IMIconnect, "getSDKVersion", "sdkVersion")
      || window.WEBEX_CONNECT_SDK_VERSION
      || "Unavailable";
    appendSetting("SDK version", sdkVersion);
    appendSetting("Application ID", appId);
    appendSetting("Connection", lastConnectionStatus);
    appendSetting("Registered", IMI.IMIconnect && typeof IMI.IMIconnect.isRegistered === "function" ? (IMI.IMIconnect.isRegistered() ? "Yes" : "No") : "Unavailable");
    appendSetting("User ID", config.userId || "Runtime supplied");
    appendSetting("Customer ID", config.customerId || "Not configured");
  }

  async function requestPushPermission() {
    if (!messaging || typeof messaging.requestPushPermission !== "function") {
      showAlert("Push permission is not available in this SDK configuration.");
      return;
    }
    if (requestPush) requestPush.disabled = true;
    try {
      await call(messaging, "requestPushPermission", []);
      showAlert("Notification permission request completed.");
    } catch (error) {
      showAlert(`Unable to enable notifications: ${errorText(error)}`);
    } finally {
      if (requestPush) requestPush.disabled = false;
    }
  }

  function displayConnectionStatus(connectionStatus) {
    let statusValue = connectionStatus;
    if (typeof statusValue === "number") {
      const statuses = window.IMI && IMI.ICConnectionStatus;
      const statusName = statuses && Object.keys(statuses).find((name) => statuses[name] === statusValue);
      statusValue = statusName || statusValue;
    } else if (statusValue && typeof statusValue === "object") {
      statusValue = firstText(statusValue, ["getName", "name", "status", "value"]) || statusValue;
    }
    const value = lower(statusValue);
    if (value.includes("connected")) return "Connected";
    if (value.includes("connect")) return "Connecting";
    if (value.includes("closed")) return "Disconnected";
    if (value.includes("refused") || value.includes("error")) return "Connection error";
    return String(statusValue || "Starting");
  }

  function registrationIdentity(userId, customerId, deviceId) {
    return JSON.stringify({
      appId: currentApplicationId(),
      userId: userId || "",
      customerId: customerId || "",
      deviceId: deviceId || ""
    });
  }

  function currentApplicationId() {
    return config.appId || config.applicationId || (config.asset && config.asset.appId) || "";
  }

  function stableDeviceId(userId, customerId) {
    if (config.deviceId) return config.deviceId;
    const appId = currentApplicationId();
    return `webex-${hashIdentity(`${appId}|${userId}|${customerId || ""}`)}`;
  }

  async function switchSdkRegistration(userId, customerId) {
    if (messaging && typeof messaging.isConnected === "function" && messaging.isConnected() && typeof messaging.disconnect === "function") {
      messaging.disconnect();
    }
    if (typeof IMI.IMIconnect.unregister === "function") {
      const result = IMI.IMIconnect.unregister();
      if (result && typeof result.then === "function") await result;
      return false;
    }
    if (typeof IMI.IMIconnect.updateProfileData === "function") {
      await call(IMI.IMIconnect, "updateProfileData", ["UserId", userId]);
      if (customerId) {
        await call(IMI.IMIconnect, "updateProfileData", ["CustomerId", customerId]);
      } else if (typeof IMI.IMIconnect.removeProfileData === "function") {
        await call(IMI.IMIconnect, "removeProfileData", ["CustomerId"]);
      }
      return true;
    }
    throw new Error("Webex Connect SDK cannot switch the registered visitor in this browser session.");
  }

  async function ensureRegistration() {
    const userId = config.userId || `web-user-${Date.now()}`;
    const customerId = config.customerId || "";
    const deviceId = stableDeviceId(userId, customerId);
    const identity = registrationIdentity(userId, customerId, deviceId);
    let registered = IMI.IMIconnect.isRegistered();
    const previousIdentity = readStorage(registrationStorageKey);
    if (registered && previousIdentity !== identity) {
      registered = await switchSdkRegistration(userId, customerId);
    }
    if (!registered) {
      const profile = new IMI.ICDeviceProfile(deviceId, userId, customerId || undefined);
      await call(IMI.IMIconnect, "register", [profile]);
    }
    writeStorage(registrationStorageKey, identity);
  }

  function storedRegistrationIdentity() {
    const value = readStorage(registrationStorageKey);
    if (!value) return null;
    try {
      return JSON.parse(value);
    } catch {
      return null;
    }
  }

  function isCurrentApplicationIdentity(identity) {
    if (!identity || !identity.userId) return false;
    const appId = currentApplicationId();
    return !identity.appId || !appId || identity.appId === appId;
  }

  function applyIdentity(identity) {
    if (!identity) return;
    config.userId = identity.userId || "";
    config.customerId = identity.customerId || "";
    config.deviceId = identity.deviceId || "";
  }

  function populateLogin(identity) {
    if (loginUserId) loginUserId.value = identity && identity.userId ? identity.userId : (config.userId || "");
    if (loginCustomerId) loginCustomerId.value = identity && identity.customerId ? identity.customerId : (config.customerId || "");
    if (loginDeviceId) loginDeviceId.value = identity && identity.deviceId ? identity.deviceId : (config.deviceId || "");
  }

  async function preparePanelSession() {
    if (isInitialized) return;
    setLoginVisible(true);
    showLoginError("");
    try {
      if (!window.IMI || !IMI.IMIconnect || !IMI.ICMessaging) {
        throw new Error("Webex Connect JavaScript SDK is not loaded. Install SDK assets and imi-environments.js.");
      }
      IMI.IMIconnect.startup();
      const registeredIdentity = storedRegistrationIdentity();
      if (IMI.IMIconnect.isRegistered() && isCurrentApplicationIdentity(registeredIdentity)) {
        applyIdentity(registeredIdentity);
        setLoginVisible(false);
        await init();
        return;
      }
      populateLogin(isCurrentApplicationIdentity(registeredIdentity) ? registeredIdentity : null);
    } catch (error) {
      showLoginError(errorText(error));
    }
  }

  async function clearSession(closePanel) {
    if (messaging && typeof messaging.isConnected === "function" && messaging.isConnected() && typeof messaging.disconnect === "function") {
      messaging.disconnect();
    }
    if (window.IMI && IMI.IMIconnect && typeof IMI.IMIconnect.unregister === "function") {
      const result = IMI.IMIconnect.unregister();
      if (result && typeof result.then === "function") await result;
    }
    removeStorage(registrationStorageKey);
    removeStorage(getStorageKey());
    messaging = null;
    threads = [];
    currentThread = null;
    currentMessages = [];
    currentMessageKeys = new Set();
    connected = false;
    isInitialized = false;
    lastConnectionStatus = "Signed out";
    setStatus("Signed out");
    showAlert("");
    config.userId = "";
    config.customerId = "";
    config.deviceId = "";
    populateLogin(null);
    setLoginVisible(true);
    if (closePanel) {
      panel.hidden = true;
      launcher.setAttribute("aria-expanded", "false");
    } else if (loginUserId) {
      window.setTimeout(() => loginUserId.focus(), 0);
    }
  }

  function handleIncoming(message) {
    const type = messageType(message);
    const id = messageThreadId(message);
    updateThreadFromMessage(message);
    if (type.includes("typingstart")) {
      if (typing) typing.hidden = false;
      return;
    }
    if (type.includes("typingstop")) {
      if (typing) typing.hidden = true;
      return;
    }
    if (type.includes("updatethread") || type.includes("reopenthread") || type.includes("closethread")) {
      const affected = threads.find((thread) => threadId(thread) === id);
      if (affected) affected.__wcStatus = type.includes("closethread") ? "Closed" : "Active";
      if (currentThread && id === threadId(currentThread)) {
        currentThread.__wcStatus = type.includes("closethread") ? "Closed" : "Active";
        renderConversationHeader();
      }
      loadThreads().catch(() => {});
      return;
    }
    if (!currentThread || id !== threadId(currentThread)) return;
    if (isReceiptOrLifecycle(type)) {
      const relatedId = readValue(message, "getRelatedTransactionId", "relatedTransactionId", "getTransactionId", "transactionId");
      const related = currentMessages.find((item) => readValue(item, "getTransactionId", "transactionId") === relatedId);
      if (related) {
        related.__wcStatus = type.includes("read") ? "Read" : type.includes("deliver") ? "Delivered" : "Clicked";
        renderMessages();
      }
      return;
    }
    mergeMessages([message]);
    renderMessages();
    const transactionId = readValue(message, "getTransactionId", "transactionId");
    if (transactionId && messaging.setMessageAsRead) call(messaging, "setMessageAsRead", [transactionId]).catch(() => {});
  }

  async function init() {
    if (isInitialized) return;
    if (!window.IMI || !IMI.IMIconnect || !IMI.ICMessaging) {
      throw new Error("Webex Connect JavaScript SDK is not loaded. Install SDK assets and imi-environments.js.");
    }
    initializeProfileHeader();
    setStatus("Starting");
    setComposerEnabled(false);
    IMI.IMIconnect.startup();
    if (config.securityToken) IMI.IMIconnect.setSecurityToken(config.securityToken);
    messaging = IMI.ICMessaging.getInstance();
    messaging.setICMessagingReceiver({
      onConnectionStatusChanged: (connectionStatus) => {
        const label = displayConnectionStatus(connectionStatus);
        const sdkConnected = typeof messaging.isConnected === "function" && messaging.isConnected();
        connected = label === "Connected" || sdkConnected;
        lastConnectionStatus = connected ? "Connected" : label;
        setStatus(lastConnectionStatus);
        renderConversationHeader();
      },
      onMessageReceived: handleIncoming
    });
    await ensureRegistration();
    if (!messaging.isConnected()) messaging.connect();
    connected = true;
    lastConnectionStatus = "Connected";
    setStatus("Connected");
    await loadThreads();
    renderConversationHeader();
    isInitialized = true;
  }

  launcher.addEventListener("click", async () => {
    const shouldOpen = panel.hidden;
    panel.hidden = !shouldOpen;
    launcher.setAttribute("aria-expanded", String(shouldOpen));
    if (shouldOpen) {
      await preparePanelSession();
      if (isInitialized && currentThread && input) input.focus();
    }
  });

  closeButton.addEventListener("click", () => {
    panel.hidden = true;
    launcher.setAttribute("aria-expanded", "false");
  });

  newThreadButton.addEventListener("click", openTitleModal);
  refreshThreadsButton.addEventListener("click", () => loadThreads().catch((error) => showAlert(errorText(error))));
  closeThreadButton.addEventListener("click", () => closeCurrentThread());
  reopenThreadButton.addEventListener("click", () => reopenCurrentThread());
  titleCancelButtons.forEach((button) => button.addEventListener("click", closeTitleModal));
  titleForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const title = titleInput.value.trim();
    if (!title) {
      titleError.hidden = false;
      titleInput.focus();
      return;
    }
    titleError.hidden = true;
    titleSubmit.disabled = true;
    try {
      await createNewThread(title);
      closeTitleModal();
    } finally {
      titleSubmit.disabled = false;
    }
  });
  settingsOpen.addEventListener("click", () => {
    refreshSettings();
    setSettingsVisible(true);
  });
  settingsClose.addEventListener("click", () => setSettingsVisible(false));
  expandButton.addEventListener("click", () => setExpanded(!isExpanded));
  requestPush.addEventListener("click", requestPushPermission);
  switchUserButton.addEventListener("click", async () => {
    try {
      await clearSession(false);
    } catch (error) {
      showAlert(`Unable to switch user: ${errorText(error)}`);
    }
  });
  logoutButton.addEventListener("click", async () => {
    try {
      await clearSession(true);
    } catch (error) {
      showAlert(`Unable to log out: ${errorText(error)}`);
    }
  });
  backButton.addEventListener("click", () => {
    currentThread = null;
    removeStorage(getStorageKey());
    setConversationVisible(false);
    setComposerEnabled(false);
    renderThreadList();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const text = input.value.trim();
    if (!text || !messaging || !currentThread) return;
    input.value = "";
    const message = new IMI.ICMessage();
    message.setMessage(text);
    message.setThread(currentThread);
    if (message.setOutgoing) message.setOutgoing(true);
    appendOptimisticMessage(message);
    try {
      await call(messaging, "publishMessage", [message]);
    } catch (error) {
      message.__wcStatus = "Not sent";
      renderMessages();
      showAlert(errorText(error));
    }
  });

  emojiButton.addEventListener("click", () => {
    if (!input || input.disabled) return;
    const start = input.selectionStart || input.value.length;
    const end = input.selectionEnd || start;
    input.value = `${input.value.slice(0, start)}🙂${input.value.slice(end)}`;
    input.selectionStart = input.selectionEnd = start + 2;
    input.focus();
  });

  async function startSession(event) {
    if (event) event.preventDefault();
    const userId = loginUserId && loginUserId.value.trim();
    if (!userId) {
      showLoginError("Enter a User ID to continue.");
      if (loginUserId) loginUserId.focus();
      return;
    }
    config.userId = userId;
    config.customerId = loginCustomerId ? loginCustomerId.value.trim() : "";
    config.deviceId = loginDeviceId ? loginDeviceId.value.trim() : "";
    showLoginError("");
    if (loginSubmit) loginSubmit.disabled = true;
    setLoginVisible(false);
    try {
      await init();
    } catch (error) {
      connected = false;
      setStatus("Configuration required");
      setComposerEnabled(false);
      setLoginVisible(true);
      showLoginError(errorText(error));
    } finally {
      if (loginSubmit) loginSubmit.disabled = false;
    }
  }

  populateLogin(storedRegistrationIdentity());
  if (loginForm) loginForm.addEventListener("submit", startSession);
}());
