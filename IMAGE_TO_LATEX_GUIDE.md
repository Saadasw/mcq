# Image to LaTeX Extraction - User Guide

## Overview

This feature allows admin users to upload images of MCQ questions and automatically extract LaTeX code using Google's Gemini AI Vision API. This significantly speeds up the process of creating exams by eliminating manual LaTeX typing.

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

### Step 2: Create Question Inputs
1. Enter the number of questions (1-40)
2. Click **"Create Question Inputs"**
3. You'll see input fields for each question

### Step 3: Upload Image for LaTeX Extraction
For each question:

1. Click the **"📷 Upload Image & Extract LaTeX"** button
2. Select an image file containing the question:
   - Supported formats: PNG, JPG, JPEG, GIF, WEBP
   - Recommended: High resolution, clear text
   - Can contain: Bengali text, English text, math formulas, diagrams

3. Wait for processing (usually 3-10 seconds):
   - Status shows: "⏳ Uploading and analyzing image..."
   - The AI analyzes the image
   - LaTeX code is extracted

4. Review the extracted LaTeX:
   - Code appears automatically in the textarea
   - Status shows: "✅ LaTeX extracted successfully!"
   - Edit the code if needed

5. Repeat for other questions

### Step 4: Complete the Form
1. Add optional image URLs if needed
2. Enter correct answer keys (1-4)
3. Fill in exam metadata (name, subject, duration)
4. Click **"Compile & Show Output"**

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

### Input Image:
```
১. যদি x + y = 10 এবং x - y = 2 হয়, তাহলে x এর মান কত?
```

### Extracted LaTeX:
```latex
যদি $x + y = 10$ এবং $x - y = 2$ হয়, তাহলে $x$ এর মান কত?
```

### Another Example:

**Input Image**:
```
Find the area of a circle with radius r = 5 cm.
```

**Extracted LaTeX**:
```latex
Find the area of a circle with radius $r = 5$ cm.
```

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
- **Rate Limit**: 10 requests/minute
- **Body**:
  - `image`: Image file (PNG/JPG/JPEG/GIF/WEBP)

### Response

**Success (200)**:
```json
{
  "success": true,
  "latex_code": "যদি $x^2 + 5x + 6 = 0$ হয়..."
}
```

**Error (400/500/503)**:
```json
{
  "success": false,
  "error": "Error message here"
}
```

---

## Technical Details

### AI Model
- **Model**: Gemini 1.5 Flash
- **Provider**: Google AI
- **Type**: Multimodal (Vision + Text)
- **Capabilities**: Image analysis, OCR, LaTeX generation

### Processing Flow
```
1. User uploads image
   ↓
2. Image saved to temporary file
   ↓
3. Image uploaded to Gemini API
   ↓
4. AI analyzes image and extracts content
   ↓
5. AI converts to LaTeX format
   ↓
6. Response cleaned (remove markdown, preamble)
   ↓
7. LaTeX code returned to frontend
   ↓
8. Textarea auto-populated
   ↓
9. Temporary files deleted
```

### Prompt Engineering
The system uses a carefully crafted prompt to:
- Extract text accurately (Bengali/English)
- Convert math to proper LaTeX syntax
- Return only the question body (no options)
- Handle diagrams gracefully
- Avoid adding document preambles

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
