/**
 * VNC Message Integration
 *
 * This module integrates the VNC interface with the Agent Zero message system,
 * automatically displaying the VNC interface when VNC sessions are active or
 * when VNC-related messages are received.
 */

import { store as vncStore } from "./vncStore.js";

class VNCMessageIntegration {
  constructor() {
    this.initialized = false;
    this.vncContainerCreated = false;
    this.messageObserver = null;
  }

  /**
   * Initialize VNC message integration
   */
  async init() {
    if (this.initialized) return;

    console.log('[VNC Integration] Initializing VNC message integration');

    // Initialize VNC store
    await vncStore.init();

    // Setup message observers
    this.setupMessageObserver();

    // Check for existing VNC session on page load
    await this.checkAndDisplayExistingSession();

    this.initialized = true;
    console.log('[VNC Integration] VNC message integration initialized');
  }

  /**
   * Setup mutation observer to watch for new messages
   */
  setupMessageObserver() {
    const chatHistory = document.getElementById('chat-history');
    if (!chatHistory) {
      console.warn('[VNC Integration] Chat history element not found');
      return;
    }

    // Create mutation observer to watch for new messages
    this.messageObserver = new MutationObserver((mutations) => {
      mutations.forEach((mutation) => {
        if (mutation.type === 'childList') {
          mutation.addedNodes.forEach((node) => {
            if (node.nodeType === Node.ELEMENT_NODE) {
              this.processNewMessage(node);
            }
          });
        }
      });
    });

    // Start observing
    this.messageObserver.observe(chatHistory, {
      childList: true,
      subtree: true
    });

    console.log('[VNC Integration] Message observer setup complete');
  }

  /**
   * Process newly added message elements
   */
  processNewMessage(messageElement) {
    // Check if this is a VNC-related message
    const messageContent = messageElement.textContent || '';

    // Look for VNC session start indicators
    if (this.isVNCSessionStartMessage(messageContent)) {
      console.log('[VNC Integration] VNC session start detected in message');
      this.handleVNCSessionStart(messageElement);
    }

    // Look for VNC session end indicators
    if (this.isVNCSessionEndMessage(messageContent)) {
      console.log('[VNC Integration] VNC session end detected in message');
      this.handleVNCSessionEnd(messageElement);
    }

    // Look for VNC action messages
    if (this.isVNCActionMessage(messageContent)) {
      console.log('[VNC Integration] VNC action detected in message');
      this.updateVNCInterface();
    }
  }

  /**
   * Check if message indicates VNC session start
   */
  isVNCSessionStartMessage(content) {
    const indicators = [
      'VNC Desktop Control Session Started',
      'VNC Session Active',
      'operator:enter_session',
      'vnc session',
      'desktop control session'
    ];

    const contentLower = content.toLowerCase();
    return indicators.some(indicator => contentLower.includes(indicator.toLowerCase()));
  }

  /**
   * Check if message indicates VNC session end
   */
  isVNCSessionEndMessage(content) {
    const indicators = [
      'VNC Desktop Control Session Completed',
      'VNC Session Ended',
      'operator:exit_session',
      'session completed successfully',
      'desktop automation session has been completed'
    ];

    const contentLower = content.toLowerCase();
    return indicators.some(indicator => contentLower.includes(indicator.toLowerCase()));
  }

  /**
   * Check if message contains VNC actions
   */
  isVNCActionMessage(content) {
    const indicators = [
      'operator:',
      'VNC Action:',
      'Intent Declared:',
      'Clicked',
      'Typed',
      'Moved mouse',
      'Desktop State Updated'
    ];

    return indicators.some(indicator => content.includes(indicator));
  }

  /**
   * Handle VNC session start
   */
  async handleVNCSessionStart(messageElement) {
    // Extract session ID and task description if possible
    const content = messageElement.textContent || '';
    const sessionIdMatch = content.match(/ID:\s*([a-fA-F0-9-]+)/);
    const taskMatch = content.match(/Task:\s*(.+?)(?:\n|$)/);

    if (sessionIdMatch) {
      const sessionId = sessionIdMatch[1];
      console.log('[VNC Integration] Detected session ID:', sessionId);

      // Update VNC store state
      if (!vncStore.isActive) {
        // Check session status via API
        await this.refreshVNCStatus();
      }
    }

    // Inject VNC interface after this message
    await this.injectVNCInterface(messageElement);
  }

  /**
   * Handle VNC session end
   */
  async handleVNCSessionEnd(messageElement) {
    console.log('[VNC Integration] Handling VNC session end');

    // Hide VNC interface
    this.hideVNCInterface();

    // Reset VNC store state
    await vncStore.resetSessionState();
  }

  /**
   * Update VNC interface with latest data
   */
  async updateVNCInterface() {
    if (vncStore.isActive) {
      // Refresh action log and screenshot
      await vncStore.loadActionLog();
      await vncStore.updateScreenshot();
    }
  }

  /**
   * Inject VNC interface into the chat
   */
  async injectVNCInterface(afterElement) {
    if (this.vncContainerCreated) {
      // Just show existing container
      this.showVNCInterface();
      return;
    }

    console.log('[VNC Integration] Injecting VNC interface');

    // Create VNC container
    const vncContainer = document.createElement('div');
    vncContainer.id = 'vnc-message-container';
    vncContainer.className = 'message-container vnc-container';

    // Load VNC interface HTML
    try {
      const response = await fetch('/components/vnc/vnc-interface.html');
      const vncHTML = await response.text();
      vncContainer.innerHTML = vncHTML;

      // Insert after the specified message element
      if (afterElement.nextSibling) {
        afterElement.parentNode.insertBefore(vncContainer, afterElement.nextSibling);
      } else {
        afterElement.parentNode.appendChild(vncContainer);
      }

      this.vncContainerCreated = true;

      // Initialize Alpine.js for the new component
      if (window.Alpine) {
        window.Alpine.initTree(vncContainer);
      }

      console.log('[VNC Integration] VNC interface injected successfully');

    } catch (error) {
      console.error('[VNC Integration] Failed to inject VNC interface:', error);
    }
  }

  /**
   * Show VNC interface
   */
  showVNCInterface() {
    const container = document.getElementById('vnc-message-container');
    if (container) {
      container.style.display = 'block';
      console.log('[VNC Integration] VNC interface shown');
    }
  }

  /**
   * Hide VNC interface
   */
  hideVNCInterface() {
    const container = document.getElementById('vnc-message-container');
    if (container) {
      container.style.display = 'none';
      console.log('[VNC Integration] VNC interface hidden');
    }
  }

  /**
   * Check for existing VNC session on page load
   */
  async checkAndDisplayExistingSession() {
    try {
      await this.refreshVNCStatus();

      if (vncStore.isActive) {
        console.log('[VNC Integration] Existing VNC session detected');

        // Find the last message in chat history
        const chatHistory = document.getElementById('chat-history');
        if (chatHistory && chatHistory.children.length > 0) {
          const lastMessage = chatHistory.children[chatHistory.children.length - 1];
          await this.injectVNCInterface(lastMessage);
        }
      }
    } catch (error) {
      console.log('[VNC Integration] No existing VNC session found');
    }
  }

  /**
   * Refresh VNC status from API
   */
  async refreshVNCStatus() {
    try {
      const response = await fetch('/api/vnc/session-status');
      const data = await response.json();

      if (data.is_active && data.session_id) {
        // Update store with session data
        vncStore.isActive = true;
        vncStore.sessionId = data.session_id;
        vncStore.taskDescription = data.task_description || '';
        vncStore.startTime = new Date(data.start_time);
        vncStore.currentScreenshot = data.screenshot_path;
        vncStore.annotatedScreenshot = data.annotated_screenshot_path;
        vncStore.screenDimensions = data.screen_dimensions || { width: 1280, height: 1280 };

        // Load action log
        await vncStore.loadActionLog();

        // Start polling
        vncStore.startPolling();

        return true;
      }

      return false;
    } catch (error) {
      console.error('[VNC Integration] Failed to refresh VNC status:', error);
      return false;
    }
  }

  /**
   * Cleanup integration
   */
  cleanup() {
    if (this.messageObserver) {
      this.messageObserver.disconnect();
      this.messageObserver = null;
    }

    this.hideVNCInterface();
    this.initialized = false;

    console.log('[VNC Integration] VNC message integration cleaned up');
  }
}

// Create and export singleton instance
const vncMessageIntegration = new VNCMessageIntegration();

// Auto-initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => {
    vncMessageIntegration.init();
  });
} else {
  // DOM is already ready
  vncMessageIntegration.init();
}

export default vncMessageIntegration;
