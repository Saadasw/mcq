# Session Persistence Feature Documentation

## Overview

The session persistence feature allows students to resume their exam from where they left off, even after refreshing the page or closing the browser. The system tracks exam sessions in the backend and stores answers locally in the browser, ensuring a seamless exam experience.

## Key Features

1. **Session Tracking**: Backend tracks when each student starts an exam session
2. **Answer Persistence**: Answers are automatically saved to browser localStorage
3. **Timer Continuity**: Timer continues counting from backend, accounting for time away
4. **Auto-Resume**: Automatically resumes exam state when student returns
5. **Session Expiry**: Sessions expire after 30 minutes for security

## How It Works

### Backend Session Tracking

#### Session Storage
- **Location**: `web/sessions/exam_sessions.csv`
- **Format**: CSV file with columns: `Student_ID`, `Session_ID`, `Start_Time`, `Date`
- **Purpose**: Tracks when each student started their exam session

#### Example Session Record
```csv
Student_ID,Session_ID,Start_Time,Date
12345,session_abc123,2024-01-15 10:30:45,2024-01-15
12346,session_abc123,2024-01-15 10:35:12,2024-01-15
```

### Frontend Answer Storage

#### LocalStorage Keys
- **Answers**: `exam_answers_{session_id}` - Stores selected answers with timestamp
- **Student ID**: `exam_student_id_{session_id}` - Stores student ID for auto-fill

#### Answer Storage Format
```json
{
  "answers": {
    "cell0": "ক",
    "cell1": "খ",
    "cell2": "গ",
    "cell3": "ঘ"
  },
  "timestamp": 1705312245000
}
```

## API Endpoints

### 1. Start Session
**Endpoint**: `POST /start-session`

**Request Body**:
```json
{
  "student_id": "12345",
  "session_id": "session_abc123"
}
```

**Response**:
```json
{
  "success": true,
  "start_time": "2024-01-15 10:30:45",
  "is_new": true
}
```

**Functionality**:
- Creates a new session entry if it doesn't exist
- Returns existing session if student already started
- Records start time in CSV file

### 2. Check Session
**Endpoint**: `POST /check-session`

**Request Body**:
```json
{
  "student_id": "12345",
  "session_id": "session_abc123"
}
```

**Response (Session Exists)**:
```json
{
  "success": true,
  "exists": true,
  "start_time": "2024-01-15 10:30:45",
  "remaining_seconds": 1200,
  "elapsed_seconds": 300
}
```

**Response (Session Expired - >30 minutes)**:
```json
{
  "success": true,
  "exists": false,
  "expired": true
}
```

**Response (Time Up - >25 minutes)**:
```json
{
  "success": true,
  "exists": true,
  "time_up": true,
  "remaining_seconds": 0
}
```

**Response (No Session)**:
```json
{
  "success": true,
  "exists": false
}
```

**Functionality**:
- Checks if session exists for student
- Calculates remaining time based on start time
- Returns session status (active, expired, time up)

### 3. Save Answers
**Endpoint**: `POST /save-answers`

**Request Body**:
```json
{
  "student_id": "12345",
  "session_id": "session_abc123",
  "answers": {
    "cell0": "ক",
    "cell1": "খ",
    "cell2": "গ",
    "cell3": "ঘ"
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "Answers saved successfully"
}
```

## Frontend Implementation

### Session Lifecycle

#### 1. Page Load
```javascript
// Auto-load student ID from localStorage
loadStudentIdFromStorage();

// Check for existing session
if (studentIdInput.value.trim()) {
  checkExistingSession();
}
```

#### 2. Start Exam
```javascript
// When student clicks "Start Exam" button:
1. Save student ID to localStorage
2. Call /start-session endpoint
3. If session exists, get remaining time from backend
4. Start timer countdown
5. Remove PDF blur
6. Enable radio buttons
7. Load saved answers from localStorage
```

#### 3. During Exam
```javascript
// Auto-save answers:
- Every 10 seconds automatically
- When radio button changes
- Stored in localStorage with timestamp

// Timer sync:
- Syncs with backend every 30 seconds
- Ensures accuracy even if page is inactive
```

#### 4. Page Refresh/Return
```javascript
// On page load:
1. Load student ID from localStorage
2. Check backend for existing session
3. Calculate remaining time
4. Restore answers from localStorage
5. Resume timer automatically
6. Show "Session resumed" message
```

### Key Functions

#### `checkExistingSession()`
- Checks backend for existing session
- Calculates remaining time
- Restores exam state if session exists
- Handles expired/time-up scenarios

#### `saveAnswersToStorage()`
- Saves current answers to localStorage
- Includes timestamp for expiry check
- Called automatically every 10 seconds

#### `loadAnswersFromStorage()`
- Loads answers from localStorage
- Checks if data is expired (30 minutes)
- Restores radio button selections

#### `syncTimerWithBackend()`
- Syncs timer with backend every 30 seconds
- Ensures accuracy across page refreshes
- Updates remaining time from server

## Time Calculation Logic

### Exam Duration
- **Total Time**: 25 minutes (1500 seconds)
- **Session Expiry**: 30 minutes (1800 seconds)

### Remaining Time Calculation
```python
elapsed_seconds = (current_time - start_time).total_seconds()
remaining_seconds = max(0, 1500 - elapsed_seconds)
```

### Scenarios

#### Scenario 1: Student starts exam, works for 10 minutes, refreshes
- **Elapsed**: 10 minutes (600 seconds)
- **Remaining**: 15 minutes (900 seconds)
- **Action**: Resume with 15 minutes remaining

#### Scenario 2: Student starts exam, leaves for 12 minutes, returns
- **Elapsed**: 12 minutes (720 seconds)
- **Remaining**: 13 minutes (780 seconds)
- **Action**: Resume with 13 minutes remaining

#### Scenario 3: Student starts exam, leaves for 26 minutes, returns
- **Elapsed**: 26 minutes (1560 seconds)
- **Remaining**: 0 seconds (time up)
- **Action**: Show "Time is up" message, disable inputs

#### Scenario 4: Student starts exam, leaves for 31 minutes, returns
- **Elapsed**: 31 minutes (1860 seconds)
- **Remaining**: N/A (session expired)
- **Action**: Show "Session expired" message, clear localStorage

## File Structure

```
web/
├── sessions/
│   ├── exam_sessions.csv          # Backend session tracking
│   └── README_SESSION.md          # This file
├── answers/
│   └── answers_{session_id}.csv   # Final answer submissions
├── app.py                         # Flask backend with session endpoints
└── templates/
    └── output.html                # Frontend with session persistence
```

## Security Considerations

1. **Session Expiry**: Sessions expire after 30 minutes to prevent abuse
2. **Backend Validation**: Timer is validated against backend, not just frontend
3. **Answer Storage**: Answers stored locally but validated on submission
4. **Time Tracking**: Server-side time tracking prevents client-side manipulation

## Usage Flow

### First Time Starting Exam
1. Student enters Student ID
2. Student clicks "Start Exam" button
3. Backend creates session entry with start time
4. Timer starts at 25:00
5. Answers saved to localStorage as student selects them

### Returning After Refresh
1. Student refreshes page or returns later
2. Student ID auto-loaded from localStorage
3. Backend checks for existing session
4. Remaining time calculated (25 minutes - elapsed time)
5. Answers restored from localStorage
6. Timer resumes automatically
7. Student continues from where they left off

### Time Expiry Scenarios
- **< 25 minutes elapsed**: Resume with remaining time
- **25-30 minutes elapsed**: Time up, exam ended
- **> 30 minutes elapsed**: Session expired, must start new exam

## Benefits

1. **User Experience**: Students don't lose progress on refresh
2. **Reliability**: Backend tracking ensures accurate timekeeping
3. **Flexibility**: Students can take breaks (within time limit)
4. **Data Safety**: Answers saved locally and on server
5. **Security**: Time limits enforced server-side

## Technical Details

### Backend Implementation
- **Language**: Python (Flask)
- **Storage**: CSV files for simplicity
- **Time Tracking**: Server-side datetime for accuracy
- **Session Management**: File-based (can be upgraded to database)

### Frontend Implementation
- **Storage**: Browser localStorage API
- **Sync**: Periodic backend sync every 30 seconds
- **Auto-save**: Answers saved every 10 seconds
- **Resume**: Automatic session detection and restoration

### Browser Compatibility
- **localStorage**: Supported in all modern browsers
- **Auto-save**: Works even if browser is closed
- **Session Resume**: Works across browser sessions (within 30 min)

## Future Enhancements

1. **Database Storage**: Migrate from CSV to database for better performance
2. **Multiple Sessions**: Allow students to have multiple active sessions
3. **Session History**: Track all session attempts
4. **Admin Dashboard**: View active sessions and student progress
5. **Real-time Sync**: WebSocket for real-time timer updates

## Troubleshooting

### Issue: Answers not restoring after refresh
**Solution**: Check browser localStorage is enabled and not cleared

### Issue: Timer shows incorrect time
**Solution**: Timer syncs every 30 seconds, wait for next sync or refresh page

### Issue: Session expired message appears too early
**Solution**: Check server time is correct, session expires after 30 minutes from start

### Issue: Answers not saving
**Solution**: Check browser console for errors, ensure localStorage is available

## Testing

### Test Case 1: Basic Session Persistence
1. Start exam with Student ID "12345"
2. Answer 2 questions
3. Refresh page
4. **Expected**: Student ID loaded, answers restored, timer continues

### Test Case 2: Time Calculation
1. Start exam
2. Wait 5 minutes
3. Refresh page
4. **Expected**: Timer shows 20:00 remaining

### Test Case 3: Session Expiry
1. Start exam
2. Wait 31 minutes
3. Refresh page
4. **Expected**: "Session expired" message, must start new exam

### Test Case 4: Time Up
1. Start exam
2. Wait 26 minutes
3. Refresh page
4. **Expected**: "Time is up" message, exam ended

## Notes

- Session data is stored in CSV format for simplicity
- localStorage has a 30-minute expiry check
- Backend session tracking is the source of truth for time
- Answers are saved both locally and on final submission
- Timer syncs with backend to prevent client-side manipulation


