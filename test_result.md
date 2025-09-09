#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: "Move the map zoom controls to the top right of the map, the button to make the map full screen should be on the bottom left of the map when the map is full screen the button to back out of full screen should be bottom left of the screen. I still see absolutely no visual radar data, I see the radars and can select them, but nothing appears no matter what type of data or radar i select. No specific requirements for the scroll option on the control menu, the collapsible menu should function exactly the same wether full screen or not full screen, leave the controls menu at top left of map, I will do manual visual testing after the fixes"

backend:
  - task: "Fix radar visual data display - no radar overlays showing"
    implemented: true
    working: false
    file: "/app/backend/server.py"
    stuck_count: 1
    priority: "high"
    needs_retesting: false
    status_history:
      - working: false
        agent: "main"
        comment: "User reports no visual radar data appears despite radar station selection working. Critical bug - radar overlays not displaying."
      - working: false
        agent: "testing"
        comment: "CRITICAL ISSUE IDENTIFIED: All radar URLs (100% failure rate) return HTTP 404 errors. Backend generates invalid radar URLs using incorrect timestamps and outdated API formats. NWS RIDGE URLs no longer work, RainViewer URLs use wrong timestamp format. Backend needs to use valid timestamps from RainViewer API (https://api.rainviewer.com/public/weather-maps.json) or modern NWS radar API (https://mapservices.weather.noaa.gov/eventdriven/rest/services/radar/radar_base_reflectivity_time/ImageServer). This explains why no visual radar data appears - all generated URLs are broken."

frontend:
  - task: "Move map zoom controls to top-right of map"
    implemented: false
    working: false
    file: "/app/frontend/src/components/InteractiveRadarMap.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: false
        agent: "main"
        comment: "Need to move Leaflet zoom controls from default top-left to top-right position"

  - task: "Move fullscreen button to bottom-left of map"
    implemented: false
    working: false
    file: "/app/frontend/src/components/InteractiveRadarMap.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: false
        agent: "main"
        comment: "Fullscreen button currently in control panel, needs to be moved to bottom-left corner of map"

  - task: "Make collapsible control panel scrollable"
    implemented: false
    working: false
    file: "/app/frontend/src/components/InteractiveRadarMap.js"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
      - working: false
        agent: "main"
        comment: "Control panel needs to be scrollable to prevent UI overflow"

  - task: "Fix radar visual data overlay display"
    implemented: false
    working: false
    file: "/app/frontend/src/components/InteractiveRadarMap.js"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
      - working: false
        agent: "main"
        comment: "RadarOverlay component not displaying actual radar imagery. User reports no visual radar data despite API working."

metadata:
  created_by: "main_agent"
  version: "1.0"
  test_sequence: 1
  run_ui: false

test_plan:
  current_focus:
    - "Fix radar visual data display - no radar overlays showing"
    - "Move map zoom controls to top-right of map"
    - "Move fullscreen button to bottom-left of map"
    - "Fix radar visual data overlay display"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
  - agent: "main"
    message: "Identified critical radar visualization bug - user reports no visual radar data despite working API. Starting fixes for UI positioning and radar overlay display issues."