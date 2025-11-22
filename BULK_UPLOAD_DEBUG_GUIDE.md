# Bulk Upload Button - Debugging Guide

## Overview

This guide helps diagnose and fix issues with the "Upload Full Question Paper" bulk upload button in the admin panel.

---

## Quick Test

### Option 1: Standalone Test File

Open `test_bulk_upload_button.html` directly in your browser:

```bash
# In your browser, open:
file:///home/user/mcq/test_bulk_upload_button.html

# Or if running a web server:
cd /home/user/mcq
python3 -m http.server 8000
# Then visit: http://localhost:8000/test_bulk_upload_button.html
```

**Expected Result**:
- Button should be visible and clickable
- Clicking button should open file picker
- Selecting a file should show filename in status area
- Log should show all steps succeeding

---

## Debugging in Admin Panel

### Step 1: Open Browser DevTools

1. Navigate to `/admin` (after logging in)
2. Press **F12** (or Right-click → Inspect)
3. Go to **Console** tab

### Step 2: Check Element Initialization

Look for these console messages:

```
Script loading...
Elements found: {makeBtn: true, countEl: true, inputs: true, ...}
Setting up bulk upload event listeners...
✅ Bulk upload event listeners attached successfully
Auto-initializing question inputs...
Button clicked! Count value: 4
...
Bulk upload button test:
  - Button exists: true
  - Button visible: true
  - Button enabled: true
  - Button has click listener: true
✅ Bulk upload button is ready to use!
```

**If you DON'T see these messages**:
- JavaScript error occurred during page load
- Look for red error messages in console
- Check if there are any syntax errors

### Step 3: Test Button Click

Click the "📷 Upload Full Question Paper" button.

**Expected console output**:
```
Bulk upload button clicked!
File input triggered
```

**If file picker opens**: ✅ Button works! Continue to Step 4.

**If file picker doesn't open**:
- Check if button is disabled (should not be)
- Check if click event is being caught by parent form
- Try clicking directly on button text, not just near it

### Step 4: Test File Upload

1. Select an image file (PNG, JPG, JPEG, GIF, WEBP)
2. Wait for processing (20-30 seconds)

**Expected console output**:
```
File input changed, file selected: image.png
```

**Expected status messages**:
- "⏳ Uploading and analyzing full question paper..." (blue)
- "✅ Successfully extracted N questions!" (green)
- "✅ Success! N questions extracted and populated." (green)

**If you see error messages**:
- See "Common Errors" section below

---

## Common Errors

### Error: "Gemini API not configured"

**Full message**: `❌ Error: Gemini API not configured. Please set GEMINI_API_KEY environment variable.`

**Cause**: The `GEMINI_API_KEY` environment variable is not set on the server.

**Solution**:

1. Get a Gemini API key from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Set the environment variable:

   **Local Development**:
   ```bash
   export GEMINI_API_KEY="AIzaSy..."
   python3 web/app.py
   ```

   **Docker**:
   ```bash
   docker run -e GEMINI_API_KEY="AIzaSy..." -p 5000:5000 mcq-app
   ```

   **Railway/Render**:
   - Go to project settings → Environment Variables
   - Add: `GEMINI_API_KEY` = `AIzaSy...`
   - Redeploy

3. Restart the server
4. Verify setup in logs: `✅ Gemini API configured successfully`

---

### Error: "Invalid file type"

**Full message**: `❌ Error: Invalid file type. Allowed: PNG, JPG, JPEG, GIF, WEBP`

**Cause**: Uploaded file is not an image.

**Solution**: Only upload image files. Do not upload PDFs, Word documents, etc.

---

### Error: "Could not extract individual questions"

**Full message**: `❌ Error: Could not extract individual questions. Please try a clearer image or upload questions separately.`

**Cause**: AI failed to parse the LaTeX output into individual questions.

**Possible reasons**:
1. Image quality is too poor
2. Text is too blurry or distorted
3. Complex layout confuses the AI
4. Unsupported language or symbols

**Solutions**:
1. **Use higher resolution image** (300+ DPI recommended)
2. **Ensure good lighting and contrast** in the image
3. **Try a simpler layout** (single column, clear numbering)
4. **Crop image** to remove headers/footers
5. **Use manual entry** if AI extraction fails repeatedly

---

### Error: "Network error"

**Full message**: `❌ Network error. Please try again.`

**Cause**: Failed to connect to the server or server crashed.

**Solutions**:
1. Check if server is running
2. Check browser console for detailed error
3. Check server logs for error messages
4. Verify network connectivity
5. Try refreshing the page

---

### Button Doesn't Respond to Clicks

**Symptoms**:
- Button is visible but nothing happens when clicked
- No file picker opens
- No console logs appear

**Debugging**:

1. **Check if JavaScript loaded**:
   Open console and type:
   ```javascript
   document.getElementById('bulk-upload-btn')
   ```
   - If `null`: Element doesn't exist (HTML error)
   - If `<button>`: Element exists ✓

2. **Check if event listeners attached**:
   Look for this log: `✅ Bulk upload event listeners attached successfully`
   - If not present: JavaScript error prevented listener attachment

3. **Manually trigger file picker**:
   Open console and run:
   ```javascript
   document.getElementById('bulk-upload-input').click()
   ```
   - If file picker opens: Event listener issue
   - If nothing happens: Browser security blocking file input

4. **Check for form interference**:
   The button is inside a `<form>`. Check if form is capturing the click.
   - Button has `type="button"` (should prevent form submission)
   - Click handler has `e.preventDefault()` and `e.stopPropagation()`

5. **Check for CSS hiding**:
   Open DevTools → Elements tab → Find the button → Check computed styles
   - Verify `display` is not `none`
   - Verify `visibility` is not `hidden`
   - Verify `opacity` is not `0`

---

### Hover Effect Doesn't Work

**Symptoms**: Button doesn't change color when hovering

**Cause**: CSS hover effects or JavaScript event listeners not working

**Debugging**:
1. Check console for JavaScript errors
2. Verify these logs appear:
   ```
   🖱️ Mouse entered button area
   🖱️ Mouse left button area
   ```
3. If logs appear but color doesn't change: CSS specificity issue
4. If logs don't appear: Event listeners not attached

**Note**: Hover effect is cosmetic. If button clicks work, hover effect failure is not critical.

---

## Technical Details

### Button HTML Structure

```html
<button id="bulk-upload-btn" type="button" style="...">
  📷 Upload Full Question Paper
</button>
<input id="bulk-upload-input" type="file" accept="image/*" style="display: none;" />
<div id="bulk-upload-status" style="..."></div>
```

### Event Flow

1. User clicks button → `click` event fires
2. JavaScript prevents default form submission
3. JavaScript triggers hidden file input click
4. Browser opens file picker
5. User selects file → `change` event fires on file input
6. JavaScript reads file and sends to `/extract-latex` endpoint
7. Server processes image with Gemini AI (20-30 seconds)
8. Server returns JSON with extracted questions
9. JavaScript populates all LaTeX textareas
10. Page scrolls to question inputs

### API Endpoint

```
POST /extract-latex
Content-Type: multipart/form-data
Authentication: Admin session required
Rate Limit: 5 requests/minute

Request Body:
  image: <file> (PNG/JPG/JPEG/GIF/WEBP)

Response (Success):
{
  "success": true,
  "question_count": 10,
  "questions": ["LaTeX snippet 1", "LaTeX snippet 2", ...]
}

Response (Error):
{
  "success": false,
  "error": "Error message here"
}
```

---

## Browser Compatibility

**Tested Browsers**:
- ✅ Chrome 90+
- ✅ Firefox 88+
- ✅ Safari 14+
- ✅ Edge 90+

**Known Issues**:
- ⚠️ IE 11: Not supported (no modern JavaScript support)
- ⚠️ Very old browsers: May not support file input click() method

---

## Performance Notes

- **Processing Time**: 20-30 seconds for full question paper
- **File Size Limit**: No strict limit, but larger files take longer
- **Recommended**: Images under 5 MB for best performance
- **Rate Limit**: 5 uploads per minute to prevent API abuse

---

## Troubleshooting Checklist

Use this checklist to systematically debug issues:

- [ ] Server is running and accessible
- [ ] Logged in as admin (not guest)
- [ ] Browser console is open
- [ ] Console shows "✅ Bulk upload button is ready to use!"
- [ ] Button is visible on page
- [ ] Button is not disabled
- [ ] Clicking button logs "Bulk upload button clicked!"
- [ ] File picker opens when button is clicked
- [ ] Selecting file logs "File input changed, file selected: ..."
- [ ] GEMINI_API_KEY is set on server
- [ ] Image file is valid format (PNG/JPG/etc.)
- [ ] No JavaScript errors in console (red messages)
- [ ] Network tab shows `/extract-latex` request sent
- [ ] Server logs show request received
- [ ] Response is received (check Network tab)

**If all checked**: Button is working! Any errors are likely API or image quality issues.

**If any unchecked**: Focus on that step for debugging.

---

## Getting Help

If you've tried all troubleshooting steps and the button still doesn't work:

1. **Collect debugging info**:
   - Full browser console log (copy all text)
   - Browser name and version
   - Operating system
   - Steps to reproduce
   - Screenshot of the page

2. **Check server logs**:
   - Look for Python error messages
   - Check if server is receiving the request
   - Verify GEMINI_API_KEY configuration

3. **Test with standalone file**:
   - Open `test_bulk_upload_button.html`
   - If test works but admin panel doesn't: Issue is in admin page
   - If test also fails: Browser or environment issue

4. **Create minimal reproduction**:
   - Try in incognito/private browsing mode
   - Try in different browser
   - Try on different computer/device

---

## Recent Changes

### v1.2 (2025-11-22)
- Removed inline event handlers for better CSP compatibility
- Moved hover effects to JavaScript addEventListener
- Added helpful error message context for API configuration
- Added UI note about API key requirement
- Improved error handling with actionable instructions

### v1.1 (2025-11-22)
- Added comprehensive debugging console logs
- Added element existence validation
- Added setTimeout test for button state
- Added visual feedback for button interactions

### v1.0 (2025-11-21)
- Initial bulk upload implementation
- Two-step AI pipeline (analysis + generation)
- Full question paper processing support

---

## Summary

The bulk upload button is designed with extensive debugging and error handling. If the button doesn't work:

1. **Check browser console** for detailed logs
2. **Verify GEMINI_API_KEY** is set
3. **Test with standalone file** to isolate issue
4. **Follow troubleshooting checklist** systematically

Most issues are related to:
- Missing GEMINI_API_KEY (server configuration)
- JavaScript errors preventing initialization
- Browser security blocking file input
- Poor image quality for AI extraction

The button itself has been thoroughly tested and verified to work correctly in modern browsers.
