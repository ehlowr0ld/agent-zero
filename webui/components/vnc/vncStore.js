import { createStore } from "/js/AlpineStore.js";
import { fetchApi } from "/js/api.js";

const model = {
  // VNC Session State
  isActive: false,
  sessionId: null,
  taskDescription: '',
  startTime: null,

  // Screenshot & Visual State
  currentScreenshot: null,
  annotatedScreenshot: null,
  originalScreenshotPath: null,
  annotatedScreenshotPath: null,
  screenshotTimestamp: null,
  screenDimensions: { width: 1280, height: 1280 },
  lastScreenshotUpdate: null,

  // Action Log State
  actionLog: [],
  expandedIntents: new Set(),
  currentIntent: null,

  // UI State
  isScreenshotModalOpen: false,
  modalViewMode: 'annotated', // 'annotated' or 'plain'
  screenshotZoomLevel: 1,
  isActionLogExpanded: true,
  autoScrollActionLog: true,

  // Real-time Update State
  pollingInterval: null,
  pollingActive: false,
  updateFrequency: 2000, // 2 seconds

  // Dual Context Mode
  dualContextMode: false,

  async init() {
    await this.initialize();
  },

  // Initialize the VNC store
  async initialize() {
    console.log('[VNC Store] Initializing VNC interface store');

    // Check for existing VNC session on load
    await this.checkExistingSession();

    // Setup event listeners for real-time updates
    this.setupRealtimeUpdates();
  },

  // Session Management
  async startSession(taskDescription = '') {
    try {
      console.log('[VNC Store] Starting VNC session:', taskDescription);

      const response = await fetchApi('/api/vnc/start-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ task_description: taskDescription })
      });

      if (response.session_id) {
        this.isActive = true;
        this.sessionId = response.session_id;
        this.taskDescription = taskDescription;
        this.startTime = new Date();
        this.currentScreenshot = response.screenshot_path;
        this.annotatedScreenshot = response.annotated_screenshot_path;
        this.screenDimensions = response.screen_dimensions || this.screenDimensions;

        // Start real-time updates
        this.startPolling();

        console.log('[VNC Store] Session started successfully:', this.sessionId);
      }

      return response;
    } catch (error) {
      console.error('[VNC Store] Failed to start session:', error);
      throw error;
    }
  },

  async endSession() {
    try {
      console.log('[VNC Store] Ending VNC session:', this.sessionId);

      if (!this.sessionId) return;

      const response = await fetchApi('/api/vnc/end-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: this.sessionId })
      });

      // Stop polling and reset state
      this.stopPolling();
      this.resetSessionState();

      console.log('[VNC Store] Session ended successfully');
      return response;
    } catch (error) {
      console.error('[VNC Store] Failed to end session:', error);
      throw error;
    }
  },

  async checkExistingSession() {
    try {
      const response = await fetchApi('/api/vnc/session-status');
      if (response.is_active) {
        this.isActive = true;
        this.sessionId = response.session_id;
        this.taskDescription = response.task_description;
        this.startTime = new Date(response.start_time);
        this.currentScreenshot = response.screenshot_path;
        this.annotatedScreenshot = response.annotated_screenshot_path;
        this.screenDimensions = response.screen_dimensions || this.screenDimensions;

        // Load action log
        await this.loadActionLog();

        // Start polling for updates
        this.startPolling();

        console.log('[VNC Store] Existing session detected:', this.sessionId);
      }
    } catch (error) {
      console.log('[VNC Store] No existing session found');
    }
  },

  resetSessionState() {
    this.isActive = false;
    this.sessionId = null;
    this.taskDescription = '';
    this.startTime = null;
    this.currentScreenshot = null;
    this.annotatedScreenshot = null;
    this.actionLog = [];
    this.expandedIntents.clear();
    this.currentIntent = null;
    this.lastScreenshotUpdate = null;
  },

  // Action Log Management
  async loadActionLog() {
    if (!this.sessionId) return;

    try {
      const response = await fetchApi(`/api/vnc/action-log/${this.sessionId}`);
      this.actionLog = response.action_log || [];
      this.currentIntent = response.current_intent;
      console.log('[VNC Store] Action log loaded:', this.actionLog.length, 'entries');
    } catch (error) {
      console.error('[VNC Store] Failed to load action log:', error);
    }
  },

  toggleIntentExpansion(intentIndex) {
    if (this.expandedIntents.has(intentIndex)) {
      this.expandedIntents.delete(intentIndex);
    } else {
      this.expandedIntents.add(intentIndex);
    }
  },

  isIntentExpanded(intentIndex) {
    return this.expandedIntents.has(intentIndex);
  },

  // Screenshot Management
  openScreenshotModal() {
    this.isScreenshotModalOpen = true;
    this.screenshotZoomLevel = 1;
  },

  closeScreenshotModal() {
    this.isScreenshotModalOpen = false;
  },

  zoomScreenshot(delta) {
    const newZoom = this.screenshotZoomLevel + delta;
    this.screenshotZoomLevel = Math.max(0.5, Math.min(3.0, newZoom));
  },

    // Real-time Updates via Poll System
  setupRealtimeUpdates() {
    // Listen for poll updates instead of separate polling
    // VNC data will come through the standard Agent Zero poll system
    console.log('[VNC Store] Real-time updates configured via poll system');
  },

  // Update VNC state from poll data
  updateFromPollData(vncData) {
    if (!vncData) return;

    try {
      // Update session state
      this.isActive = vncData.is_active;
      this.sessionId = vncData.session_id;
      this.taskDescription = vncData.task_description || '';

      if (vncData.start_time) {
        this.startTime = new Date(vncData.start_time);
      }

             // Update screenshot data with cache-busting
       const timestampChanged = vncData.screenshot_timestamp !== this.screenshotTimestamp;
       if (vncData.original_screenshot_path !== this.originalScreenshotPath ||
           vncData.annotated_screenshot_path !== this.annotatedScreenshotPath ||
           timestampChanged) {

         this.originalScreenshotPath = vncData.original_screenshot_path;
         this.annotatedScreenshotPath = vncData.annotated_screenshot_path;
         this.screenshotTimestamp = vncData.screenshot_timestamp;

         // Add timestamp for cache-busting to ensure UI updates despite same filenames
         const cacheBuster = this.screenshotTimestamp ? `?t=${this.screenshotTimestamp}` : '';
         this.currentScreenshot = vncData.original_screenshot_path + cacheBuster;
         this.annotatedScreenshot = vncData.annotated_screenshot_path + cacheBuster;

         this.lastScreenshotUpdate = new Date();
         console.log('[VNC Store] Screenshots updated via poll with cache-busting');
       }

      // Update screen dimensions
      if (vncData.screen_dimensions) {
        this.screenDimensions = vncData.screen_dimensions;
      }

      // Update action log
      if (vncData.action_log) {
        this.actionLog = vncData.action_log;
        this.currentIntent = vncData.current_intent;
      }


    } catch (error) {
      console.error('[VNC Store] Failed to update from poll data:', error);
    }
  },

  startPolling() {
    this.pollingActive = true;
    console.log('[VNC Store] Started real-time polling');
  },

  stopPolling() {
    this.pollingActive = false;
    console.log('[VNC Store] Stopped real-time polling');
  },

  // Utility Methods
  getSessionDuration() {
    if (!this.startTime) return '0s';

    const now = new Date();
    const duration = Math.floor((now - this.startTime) / 1000);
    const minutes = Math.floor(duration / 60);
    const seconds = duration % 60;

    return minutes > 0 ? `${minutes}m ${seconds}s` : `${seconds}s`;
  },

  getActionLogSummary() {
    const intentCount = this.actionLog.length;
    const actionCount = this.actionLog.reduce((total, intent) =>
      total + (intent.actions ? intent.actions.length : 0), 0);

    return { intentCount, actionCount };
  },

  // Configuration
  setUpdateFrequency(frequency) {
    this.updateFrequency = Math.max(1000, frequency); // Minimum 1 second
  },

  toggleDualContextMode() {
    this.dualContextMode = !this.dualContextMode;
    console.log('[VNC Store] Dual context mode:', this.dualContextMode);
  }
};

// Create and export the store
export const store = createStore('vnc', model);
