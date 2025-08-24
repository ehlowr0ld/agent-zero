## VNC Action Guidance

**Workflow Pattern:**
1. **Declare Intent** - Use `operator:declare_intent` with reasoning
2. **Plan Actions** - Analyze current screenshot and annotations
3. **Execute Actions** - Perform mouse/keyboard operations
4. **Update Screen** - Use `operator:update_screen` to see results
5. **Repeat** - Continue until task completion

**Key Action Tips:**
- **Use both screenshots together**: Read the plain screenshot for clear visual context; use the annotated screenshot to identify interactive elements
- **Coordinates (critical)**:
  - Use the fractional coordinates (0.0–1.0) from annotations to locate click/drag/scroll targets precisely
  - Do not guess pixel positions — always derive positions from the annotated element bbox center or desired anchor within the bbox
  - Example: To click an element with bbox [x1, y1, x2, y2], use ((x1+x2)/2, (y1+y2)/2) as the click point
- **Action planning**: Reference the element id/name in annotations when describing actions in your thoughts
- **Focus**: Ensure the correct window/application has focus before typing (XFCE4 uses click-to-focus)
- **Timing**: Allow time for applications to respond (built-in delays exist; add `delay` action for longer waits)
  - Security tools may have longer loading times (Burp Suite, Metasploit, network scanners)
  - Terminal commands may run for extended periods (nmap scans, brute force attacks)
- **Verification**: Use `update_screen()` to verify action results after chains
- **Error Recovery**: If actions don't work as expected, update screen and reassess; consider re-identifying the element by annotations

## **CRITICAL: Evidence-Based Verification Protocol**

### **The Golden Rule: Show Me, Don't Tell Me**
**NEVER assume your actions worked. ALWAYS verify by looking at the actual screenshot.**

### **Mandatory Verification Steps:**
1. **Pre-Action State**: Document what you see NOW
   - "The sort dropdown currently shows 'High to Low'"
   - "The search box is empty"
   - "No dropdown menu is currently visible"

2. **Action Execution**: Perform your action
   - Click the intended element
   - Type the intended text
   - Execute the intended sequence

3. **Post-Action Verification**: Call `operator:update_screen` and CHECK REALITY
   - "After clicking, the dropdown now shows 'Low to High'" ✅
   - "After clicking, the dropdown still shows 'High to Low'" ❌
   - "After typing, the search box contains 'hydrogen bottle'" ✅

4. **Reality Check**: Compare expected vs actual outcome
   - If outcome matches expectation → Continue
   - If outcome doesn't match → Diagnose and retry

### **Common Verification Failures:**
❌ **"I clicked the login button, so I'm now logged in"** (ASSUMPTION)
✅ **"I clicked the login button. Looking at the new screenshot, I can see [actual result]"** (EVIDENCE)

❌ **"I selected 'Low to High' sorting"** (ASSUMPTION)
✅ **"I clicked Element 41. The sort indicator now shows 'High to Low', so my action had a different effect than intended"** (EVIDENCE)

### **When Actions Fail:**
- **Acknowledge the failure**: "My click did not achieve the intended result"
- **Describe what actually happened**: "The dropdown closed instead of changing the sort order"
- **Plan corrective action**: "I need to click the dropdown again and select a different element"
- **Visual vs Metadata Priority**: **ALWAYS prioritize visual evidence from screenshots over metadata counts**:
  - If "Active Windows: 0" but you see windows in the screenshot, the windows ARE there - proceed with interaction
  - If annotations are unavailable, analyze the plain screenshot visually for clickable elements
  - Window detection may fail but visual elements remain interactive - trust what you see
- **Security Tool Context**: Recognize tool-specific interfaces and interaction patterns:
  - Terminal prompts: `msf6 >`, `nmap>`, `sqlmap>` require different input patterns
  - GUI tools: Burp Suite tabs, Wireshark capture controls, report generation interfaces
  - Progress indicators: Scanning percentages, brute-force attempts, file transfers

**Common Patterns:**
- Click to focus → Type text → Press Return
- Right-click → Select menu item → Click
- Drag to select → Copy/Cut → Navigate → Paste
- Double-click to open → Wait for load → Continue actions
