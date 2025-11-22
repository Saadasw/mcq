# Image to LaTeX Extraction - User Guide

## Overview

This feature allows admin users to **upload images of full question papers** and automatically extract LaTeX code for **all questions at once** using Google's Gemini AI Vision API with a sophisticated two-step pipeline. This dramatically speeds up exam creation from ~10 minutes to ~30 seconds by eliminating manual LaTeX typing.

---

## Setup Instructions

### 1. Install Dependencies

The required packages are already in `requirements.txt`:

```bash
pip install google-generativeai Pillow
```

Or if using Docker:
```bash
docker build -t mcq-app .
```

### 2. Get a Gemini API Key

1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Click **"Get API Key"**
4. Click **"Create API Key in new project"** (or select existing project)
5. Copy the API key (format: `AIza...`)

**Important**: Keep this key secure! Never commit it to Git.

### 3. Set Environment Variable

**Local Development**:
```bash
export GEMINI_API_KEY="AIzaSy..."
```

**Railway/Render Deployment**:
1. Go to your project settings
2. Navigate to Environment Variables
3. Add new variable:
   - Name: `GEMINI_API_KEY`
   - Value: `AIzaSy...` (your actual key)
4. Redeploy the application

**Docker**:
```bash
docker run -e GEMINI_API_KEY="AIzaSy..." -p 5000:5000 mcq-app
```

**Render (render.yaml)**:
```yaml
services:
  - type: web
    name: mcq-app
    env: docker
    envVars:
      - key: GEMINI_API_KEY
        sync: false  # Keep secret
```

---

## How to Use

### Step 1: Login as Admin
1. Navigate to `/login`
2. Enter admin credentials
3. You'll be redirected to the admin panel

### Step 2: Upload Full Question Paper (Bulk Upload)
1. Click the **"📷 Upload Full Question Paper"** button (blue button in AI-Powered Bulk Upload section)
2. Select an image file of your complete question paper:
   - Supported formats: PNG, JPG, JPEG, GIF, WEBP
   - Recommended: High resolution, clear text
   - Can contain: 1-40 questions in any layout
   - Supported content: Bengali text, English text, math formulas, diagrams

3. Wait for processing (20-30 seconds):
   - Status shows: "⏳ Uploading and analyzing full question paper..."
   - Step 1: AI analyzes image structure (5-10 seconds)
   - Step 2: AI generates LaTeX for all questions (10-15 seconds)
   - Step 3: Questions are parsed and populated automatically (<1 second)

4. Review auto-populated fields:
   - Question count is automatically set
   - All LaTeX textareas are filled with extracted code
   - Page scrolls to question inputs
   - Status shows: "✅ Success! N questions extracted and populated"

5. Edit if needed:
   - Review each question's LaTeX code
   - Make any necessary corrections
   - Add or modify image URLs if needed

### Step 3: Complete the Form
1. Verify question count matches your paper
2. Enter correct answer keys (1-4 for each question)
3. Fill in exam metadata (name, subject, duration, passing percentage)
4. Click **"Compile & Show Output"**

### Alternative: Manual Entry
If you prefer manual entry or need to add questions individually:
1. Enter the number of questions in "Manual Entry" section
2. Click **"Create Question Inputs"**
3. Type or paste LaTeX code into each textarea

---

## What Gets Extracted

### ✅ Successfully Extracted:
- **Bengali text**: একটি সমবাহু ত্রিভুজ
- **English text**: If x² + 5x + 6 = 0
- **Mathematical formulas**: Converted to LaTeX (`$x^2$`, `\frac{a}{b}`, etc.)
- **Equations**: Both inline and display math
- **Simple diagrams**: Converted to TikZ or textual descriptions
- **Mixed content**: Bengali + English + Math

### ❌ NOT Extracted:
- **MCQ options** (ক, খ, গ, ঘ) - These are added automatically by the system
- **Page numbers, headers, footers**
- **Formatting/styling** - Only the content is extracted

---

## Example Workflow

### Full Question Paper Processing

**Input: Image of question paper with 5 questions**

**Step 1: AI Analysis Output (Internal)**
```
Total questions: 5
Numbering format: 1., 2., 3., ...

Question 1: "যদি x + y = 10 এবং x - y = 2 হয়, তাহলে x এর মান কত?"
- Formula: x + y = 10, x - y = 2
- Options: ক. 4, খ. 5, গ. 6, ঘ. 8

Question 2: "Find the area of a circle with radius r = 5 cm."
- Formula: r = 5
- Options: A. 25π cm², B. 10π cm², C. 5π cm², D. 15π cm²

... (3 more questions)
```

**Step 2: LaTeX Generation Output**
```
### QUESTION 1 ###
যদি $x + y = 10$ এবং $x - y = 2$ হয়, তাহলে $x$ এর মান কত?

### QUESTION 2 ###
Find the area of a circle with radius $r = 5$ cm.

### QUESTION 3 ###
একটি সমবাহু ত্রিভুজের একটি বাহুর দৈর্ঘ্য $5$ সেমি হলে, এর ক্ষেত্রফল কত?

### QUESTION 4 ###
If $x^2 - 5x + 6 = 0$, the roots are:

### QUESTION 5 ###
একটি আয়তক্ষেত্রের দৈর্ঘ্য $12$ মিটার এবং প্রস্থ $8$ মিটার। এর পরিসীমা কত?
```

**Step 3: Result Sent to Frontend**
```json
{
  "success": true,
  "question_count": 5,
  "questions": [
    "যদি $x + y = 10$ এবং $x - y = 2$ হয়, তাহলে $x$ এর মান কত?",
    "Find the area of a circle with radius $r = 5$ cm.",
    "একটি সমবাহু ত্রিভুজের একটি বাহুর দৈর্ঘ্য $5$ সেমি হলে, এর ক্ষেত্রফল কত?",
    "If $x^2 - 5x + 6 = 0$, the roots are:",
    "একটি আয়তক্ষেত্রের দৈর্ঘ্য $12$ মিটার এবং প্রস্থ $8$ মিটার। এর পরিসীমা কত?"
  ]
}
```

**Final: All 5 textareas auto-populated, ready for review!**

---

## Troubleshooting

### Error: "Gemini API not configured"
**Solution**:
1. Verify `GEMINI_API_KEY` is set in environment variables
2. Restart the application
3. Check logs for "✅ Gemini API configured successfully"

### Error: "Invalid file type"
**Solution**:
- Only upload image files (PNG, JPG, JPEG, GIF, WEBP)
- Don't upload PDFs or other document formats

### Error: "Failed to extract LaTeX"
**Possible causes**:
1. **Poor image quality**: Use higher resolution images
2. **Complex layout**: Simplify the image to one question
3. **Unsupported language**: Bengali and English work best
4. **API quota exceeded**: Check your Gemini API usage limits

**Solutions**:
- Crop the image to show only one question
- Increase image resolution/clarity
- Ensure good lighting and contrast
- Try a different image

### LaTeX code is incorrect
**Solutions**:
1. **Edit manually**: The extracted code can be edited in the textarea
2. **Re-upload**: Try uploading a clearer image
3. **Partial extraction**: Extract what works, manually add the rest

### Rate Limit Error
The endpoint is limited to **10 requests per minute** to prevent API abuse.
- Wait 60 seconds before trying again
- Process questions in batches

---

## API Details

### Endpoint
```
POST /extract-latex
```

### Request
- **Method**: POST (multipart/form-data)
- **Authentication**: Admin session required
- **Rate Limit**: 5 requests/minute (lower due to full paper processing)
- **Body**:
  - `image`: Image file of full question paper (PNG/JPG/JPEG/GIF/WEBP)
- **Processing Time**: 20-30 seconds (varies with question count)

### Response

**Success (200)**:
```json
{
  "success": true,
  "question_count": 10,
  "questions": [
    "যদি $x^2 + 5x + 6 = 0$ হয়, তাহলে $x$ এর মান কত?",
    "Find the area of a triangle with base $b = 10$ cm and height $h = 5$ cm.",
    "একটি বৃত্তের ব্যাসার্ধ $7$ সেমি হলে, এর পরিধি কত?",
    ...
  ]
}
```

**Error - Parsing Failed (400)**:
```json
{
  "success": false,
  "error": "Could not extract individual questions. Please try a clearer image or upload questions separately.",
  "raw_output": "### QUESTION 1\nযদি $x^2..."
}
```

**Error - API Not Configured (503)**:
```json
{
  "success": false,
  "error": "Gemini API not configured. Please set GEMINI_API_KEY environment variable."
}
```

**Error - General (500)**:
```json
{
  "success": false,
  "error": "Failed to extract LaTeX: Connection timeout"
}
```

---

## Technical Details

### AI Model
- **Model**: Gemini 1.5 Flash
- **Provider**: Google AI
- **Type**: Multimodal (Vision + Text)
- **Capabilities**: Image analysis, OCR, LaTeX generation, structure understanding

### Two-Step Processing Pipeline
```
1. User uploads full question paper image
   ↓
2. Image saved to temporary file
   ↓
3. Image uploaded to Gemini API
   ↓
4. STEP 1: Vision Analysis (5-10 seconds)
   - AI analyzes image structure
   - Identifies question count and numbering
   - Extracts text verbatim (Bengali/English)
   - Locates formulas and diagrams
   - Lists MCQ options for reference
   ↓
5. STEP 2: LaTeX Generation (10-15 seconds)
   - AI uses analysis as context
   - Generates LaTeX for each question
   - Separates with delimiter: "### QUESTION N ###"
   - Excludes MCQ options (only question stem)
   - Returns clean LaTeX snippets
   ↓
6. STEP 3: Parsing & Population (<1 second)
   - Parse LaTeX to extract individual questions
   - Try multiple delimiter patterns (### QUESTION N ###, Question N:, etc.)
   - Fallback to numbered line parsing
   - Clean each snippet (remove preamble, options, whitespace)
   ↓
7. Response sent to frontend with array of questions
   ↓
8. Frontend auto-populates all textareas
   ↓
9. Temporary files deleted
```

### Retry Logic
```
If parsing fails:
   ↓
1. Send retry prompt with clarification
2. Show first 500 chars of failed output
3. Request proper delimiter format
4. Parse again with same fallback patterns
   ↓
If still fails:
   → Return error with raw output for debugging
```

### Prompt Engineering

**Step 1 Prompt (Analysis)**:
- Request structured analysis (JSON-like format)
- Identify total question count
- Extract text exactly as shown
- Locate mathematical formulas
- Describe diagrams if present
- DO NOT generate LaTeX yet

**Step 2 Prompt (LaTeX Generation)**:
- Use Step 1 analysis as input context
- Require specific delimiter: "### QUESTION N ###"
- Extract ONLY question stem (exclude options)
- Preserve Bengali/English text
- Convert formulas to LaTeX syntax
- No preamble, no document structure
- Clean, minimal output

**Retry Prompt (Error Correction)**:
- Show failed output sample
- Emphasize correct delimiter format
- Request regeneration with fixes

---

## Best Practices

### Image Quality
✅ **Do**:
- Use high-resolution images (300+ DPI)
- Ensure good lighting and contrast
- Crop to one question per upload
- Use clear, printed text (not handwritten)

❌ **Don't**:
- Upload blurry or low-quality images
- Include multiple questions in one image
- Use heavily compressed images
- Upload images with watermarks or noise

### LaTeX Editing
After extraction:
1. **Always review** the extracted LaTeX
2. **Test compile** to ensure it works
3. **Add custom formatting** if needed (bold, colors, etc.)
4. **Check math notation** for accuracy

### Security
- Never share your `GEMINI_API_KEY` publicly
- Don't commit API keys to Git repositories
- Use environment variables or secret managers
- Monitor API usage to avoid unexpected costs

---

## Limitations

1. **API Costs**: Gemini API has usage limits and potential costs
2. **Accuracy**: AI extraction may not be 100% accurate
3. **Complex Diagrams**: Very complex geometric diagrams may need manual creation
4. **Rate Limits**: 10 requests/minute to prevent abuse
5. **Language Support**: Best results with Bengali and English
6. **Image Size**: Very large images may take longer to process

---

## Future Improvements

Planned enhancements:
- [ ] Batch processing (multiple questions at once)
- [ ] Support for table extraction
- [ ] Custom prompt templates
- [ ] Diagram auto-generation with TikZ
- [ ] OCR fallback for offline mode
- [ ] Image preprocessing (auto-crop, enhance)
- [ ] LaTeX validation before returning
- [ ] Support for other AI models (Claude, GPT-4 Vision)

---

## Support

If you encounter issues:

1. **Check logs**: Look for error messages in application logs
2. **Verify setup**: Ensure GEMINI_API_KEY is correctly set
3. **Test manually**: Try the API key in Google AI Studio
4. **Review image**: Ensure image meets quality requirements
5. **Report bug**: Create an issue with example image and error message

---

## API Pricing (Google Gemini)

As of 2024, Gemini API pricing:
- **Free tier**: 60 requests/minute, 1500 requests/day
- **After free tier**: Pay-as-you-go pricing
- **Check current rates**: [Google AI Pricing](https://ai.google.dev/pricing)

**Note**: Monitor your usage to avoid unexpected costs.

---

## Examples

### Example 1: Simple Math Question

**Image**:
```
যদি x² = 25 হয়, তাহলে x এর মান কত?
```

**Extracted LaTeX**:
```latex
যদি $x^2 = 25$ হয়, তাহলে $x$ এর মান কত?
```

**After Compilation**: Renders beautifully with Bengali text and proper math formatting.

---

### Example 2: Complex Equation

**Image**:
```
Solve: (x + 3)² - 4(x + 3) + 4 = 0
```

**Extracted LaTeX**:
```latex
Solve: $(x + 3)^2 - 4(x + 3) + 4 = 0$
```

---

### Example 3: Geometry

**Image**:
```
একটি সমকোণী ত্রিভুজের ভূমি 3 সেমি এবং উচ্চতা 4 সেমি।
এর অতিভুজের দৈর্ঘ্য কত?
```

**Extracted LaTeX**:
```latex
একটি সমকোণী ত্রিভুজের ভূমি $3$ সেমি এবং উচ্চতা $4$ সেমি।
এর অতিভুজের দৈর্ঘ্য কত?
```

---

## Summary

The Image-to-LaTeX feature:
- ✅ Saves significant time in exam creation
- ✅ Supports Bengali and English text
- ✅ Automatically converts math formulas
- ✅ Simple to use with one-click uploads
- ✅ Secure and rate-limited
- ⚠️ Requires Gemini API key setup
- ⚠️ May need manual review/editing
- ⚠️ Subject to API usage limits

**Happy exam creating! 🎓📝**
