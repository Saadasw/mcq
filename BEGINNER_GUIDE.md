# Beginner's Guide to MCQ Application

## 📚 Table of Contents

1. [What is This Project?](#what-is-this-project)
2. [What Was Built?](#what-was-built)
3. [How Does It Work?](#how-does-it-work)
4. [Project Structure](#project-structure)
5. [Key Features](#key-features)
6. [Getting Started](#getting-started)
7. [How to Use](#how-to-use)
8. [Deployment Options](#deployment-options)
9. [Understanding the Code](#understanding-the-code)
10. [Troubleshooting](#troubleshooting)
11. [Next Steps](#next-steps)

---

## What is This Project?

This is a **Multiple Choice Question (MCQ) Exam System** that allows teachers to:
- Create MCQ questions using LaTeX (a document preparation system)
- Compile questions into PDFs with Bengali language support
- Share exam links with students
- Automatically grade student answers
- Track exam sessions and results

**Think of it like:** Google Forms, but specifically designed for math/science exams with Bengali language support and automatic PDF generation.

---

## What Was Built?

### Phase 1: Basic LaTeX Compilation
- ✅ Set up LaTeX compilation system (LuaLaTeX)
- ✅ Added Bengali font support (Noto Sans Bengali)
- ✅ Created template for MCQ questions
- ✅ Built PDF generation system

### Phase 2: Web Application
- ✅ Created Flask web application
- ✅ Built input page for teachers to enter questions
- ✅ Built output page for students to take exams
- ✅ Added PDF viewing in web browser
- ✅ Made it mobile-friendly

### Phase 3: Exam Features
- ✅ Added Student ID input
- ✅ Implemented 25-minute countdown timer
- ✅ Added session persistence (saves progress if page refreshes)
- ✅ Created answer key system for automatic grading
- ✅ Added visual feedback (highlighting correct/wrong answers)
- ✅ Implemented score calculation and display

### Phase 4: Deployment & Production
- ✅ Created Docker containerization
- ✅ Added one-click run script
- ✅ Set up deployment configurations for free hosting
- ✅ Added health checks and monitoring
- ✅ Created comprehensive documentation

---

## How Does It Work?

### The Big Picture

```
Teacher → Enters Questions (LaTeX) → System Compiles to PDF → Students Take Exam → System Grades Automatically
```

### Step-by-Step Flow

1. **Teacher Side:**
   - Teacher goes to the input page
   - Enters MCQ questions in LaTeX format
   - Enters correct answers (e.g., "142" means option 1, 4, 2 for questions 1, 2, 3)
   - Clicks "Compile"
   - System generates PDFs and creates a unique session ID
   - Teacher shares the session link with students

2. **Student Side:**
   - Student opens the session link
   - Enters their Student ID
   - Clicks "Start Exam"
   - 25-minute timer starts
   - Student answers questions by selecting radio buttons (ক, খ, গ, ঘ)
   - Answers are saved automatically
   - After 25 minutes or when clicking "Save Answers", exam ends
   - System shows score and highlights wrong answers

3. **Behind the Scenes:**
   - LaTeX code is compiled to PDF using LuaLaTeX
   - PDFs are stored in `web/generated/session_xxx/pdfs/`
   - Student answers are saved in CSV files
   - Answer keys are stored separately
   - System compares answers and calculates scores

---

## Project Structure

```
mcq/
├── web/                          # Main web application
│   ├── app.py                    # Flask application (main backend)
│   ├── templates/                # HTML templates
│   │   ├── input.html           # Teacher input page
│   │   └── output.html           # Student exam page
│   ├── static/                   # CSS, JavaScript files
│   │   └── styles.css           # Styling
│   ├── generated/               # Generated PDFs (created at runtime)
│   ├── answers/                  # Student answer files (CSV)
│   ├── answer_keys/              # Correct answer keys (CSV)
│   └── sessions/                 # Exam session data (CSV)
│
├── templates/                    # LaTeX templates
│   └── snippet_template.tex      # Template for individual questions
│
├── builder/                      # PDF sheet builder (optional)
│   └── build_sheet.py            # Combines PDFs into sheets
│
├── inputs/                       # Input LaTeX snippets
│   └── snippets/
│       └── mcq_latex_snipet.tex  # Example questions
│
├── Dockerfile                    # Docker container configuration
├── docker-compose.yml            # Docker Compose setup
├── requirements.txt              # Python dependencies
├── start.sh                      # Startup script
├── run.sh                        # One-click run script
├── Makefile                      # Common commands
│
└── Configuration files:
    ├── railway.json              # Railway deployment config
    ├── render.yaml               # Render deployment config
    └── fly.toml                  # Fly.io deployment config
```

---

## Key Features

### 1. **LaTeX Question Input**
Teachers write questions using LaTeX, which supports:
- Mathematical equations: `$x^2 + y^2 = r^2$`
- Bengali text: `নিচের কোনটি সঠিক?`
- Complex formatting: matrices, fractions, integrals

### 2. **Automatic PDF Generation**
- Each question is compiled to a separate PDF
- PDFs are displayed in a grid layout
- Mobile-friendly viewing

### 3. **Session Management**
- Each exam gets a unique session ID
- Same questions for all students
- Session data persists for 30 minutes

### 4. **Timer System**
- 25-minute countdown timer
- Starts only after Student ID is entered
- Persists across page refreshes
- Backend tracks time remaining

### 5. **Automatic Grading**
- Teacher provides answer key (e.g., "1423")
- System compares student answers
- Calculates score automatically
- Shows percentage

### 6. **Visual Feedback**
- Correct answers highlighted in red (for wrong questions)
- Student's wrong answers highlighted in orange
- Clear results display

### 7. **Mobile Support**
- Responsive design
- Touch-friendly radio buttons
- Optimized PDF viewing

---

## Getting Started

### Prerequisites

You need:
- **Docker** installed ([Install Docker](https://docs.docker.com/get-docker/))
- **Git** (optional, for cloning)

### Quick Start (One Command)

```bash
# Clone the repository (if you haven't already)
git clone https://github.com/Saadasw/mcq.git
cd mcq

# Make the script executable (first time only)
chmod +x run.sh

# Run the application
./run.sh
```

That's it! The application will be available at `http://localhost:5000`

### Alternative: Using Make

```bash
make run
```

### What Happens When You Run?

1. Docker checks if everything is installed
2. Builds a Docker image with:
   - Python 3.11
   - TeX Live (LaTeX compiler)
   - Bengali fonts
   - Flask web framework
3. Starts the application
4. Shows you the access URL

---

## How to Use

### For Teachers

#### Step 1: Access the Input Page
- Open `http://localhost:5000` in your browser
- You'll see the input form

#### Step 2: Enter Questions
1. Enter the number of questions (e.g., 5)
2. For each question, enter LaTeX code like:
   ```latex
   \begin{enumerate}
   \item নিচের কোনটি $3 \times 2$ ক্রমের ম্যাট্রিক্স?
   \begin{benglienum}
   \item $\begin{pmatrix} 1 & 2 \\ 3 & 4 \end{pmatrix}$
   \item $\begin{pmatrix} 1 & 2 & 3 \\ 4 & 5 & 6 \end{pmatrix}$ \checkmark
   \item $\begin{pmatrix} 1 \\ 2 \end{pmatrix}$
   \item $\begin{pmatrix} 1 & 2 \end{pmatrix}$
   \end{benglienum}
   \end{enumerate}
   ```

#### Step 3: Enter Correct Answers
- Enter a string like "1423" where:
  - 1 = first question's correct answer is option 1
  - 4 = second question's correct answer is option 4
  - 2 = third question's correct answer is option 2
  - 3 = fourth question's correct answer is option 3

#### Step 4: Compile
- Click "Compile Questions"
- Wait for PDFs to generate
- You'll be redirected to the output page with a session link

#### Step 5: Share the Link
- Copy the URL from the address bar
- Share with students

### For Students

#### Step 1: Open the Exam Link
- Click the link provided by teacher
- You'll see all questions as PDFs

#### Step 2: Start the Exam
- Enter your Student ID
- Click "Start Exam"
- Timer starts counting down from 25:00

#### Step 3: Answer Questions
- Read each question (PDF)
- Select your answer using radio buttons: ক, খ, গ, ঘ
- Answers are saved automatically

#### Step 4: Submit
- Click "Save Answers" when done
- Or wait for timer to reach 0:00
- View your score and results

---

## Deployment Options

### Option 1: Local Development (Docker)

```bash
./run.sh
```

**Best for:** Testing, development, local use

### Option 2: Railway (Recommended for Beginners)

1. Push code to GitHub
2. Go to [Railway.app](https://railway.app)
3. Click "New Project" → "Deploy from GitHub"
4. Select your repository
5. Railway automatically deploys!

**Best for:** Quick deployment, automatic HTTPS, no configuration needed

### Option 3: Render

1. Push code to GitHub
2. Go to [Render.com](https://render.com)
3. Create "Web Service"
4. Connect GitHub repository
5. Render auto-detects configuration

**Best for:** GitHub integration, easy setup

### Option 4: Fly.io

1. Install Fly CLI: `curl -L https://fly.io/install.sh | sh`
2. Login: `flyctl auth login`
3. Deploy: `flyctl deploy`

**Best for:** Global distribution, best performance

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed instructions.

---

## Understanding the Code

### Main Components

#### 1. `web/app.py` - The Backend

This is the heart of the application. It handles:

```python
# Flask app initialization
app = Flask(__name__)

# Routes (URL endpoints)
@app.route("/")                    # Home page (input form)
@app.post("/compile")               # Compile LaTeX to PDF
@app.get("/view/<session_id>")      # View exam questions
@app.post("/save-answers")         # Save student answers
@app.get("/health")                 # Health check
```

**Key Functions:**
- `compile_and_crop_snippet()` - Compiles LaTeX to PDF
- `calculate_marks()` - Grades student answers
- `start_session()` - Starts exam timer

#### 2. `templates/snippet_template.tex` - LaTeX Template

This is the template that wraps each question:

```latex
\documentclass[12pt]{article}
\usepackage{polyglossia}
\setmainlanguage{bengali}
\newfontfamily\bengalifont[Script=Bengali]{Noto Sans Bengali}
% ... more setup ...
\begin{document}
% CONTENT_HERE  ← Your question goes here
\end{document}
```

#### 3. `Dockerfile` - Container Configuration

Defines how to build the Docker image:

```dockerfile
FROM python:3.11-slim          # Base image
# Install TeX Live and fonts
# Install Python dependencies
# Copy application code
# Set startup command
```

#### 4. Frontend Files

- `input.html` - Teacher input form
- `output.html` - Student exam interface
- `styles.css` - Styling and responsive design

### How LaTeX Compilation Works

1. Teacher enters LaTeX code
2. Code is inserted into `snippet_template.tex`
3. `lualatex` command compiles it to PDF
4. PDF is saved to `web/generated/session_xxx/pdfs/`
5. PDF is displayed in browser

### How Grading Works

1. Teacher provides answer key: "1423"
2. Student submits answers: "1432"
3. System compares:
   - Q1: 1 vs 1 ✅ (correct)
   - Q2: 4 vs 4 ✅ (correct)
   - Q3: 2 vs 3 ❌ (wrong)
   - Q4: 3 vs 2 ❌ (wrong)
4. Score: 2/4 = 50%

---

## Troubleshooting

### Problem: "Permission denied" when running Docker

**Solution:**
```bash
sudo usermod -aG docker $USER
newgrp docker
```

See [DOCKER_PERMISSIONS_EXPLAINED.md](./DOCKER_PERMISSIONS_EXPLAINED.md)

### Problem: LaTeX compilation fails

**Check:**
- Is TeX Live installed? (It should be in Docker)
- Are fonts installed? (Noto Sans Bengali)
- Check logs: `docker compose logs`

**Solution:**
```bash
# Rebuild font cache
docker compose exec mcq-app luaotfload-tool -u
```

### Problem: PDFs not displaying

**Check:**
- Are PDFs generated? Check `web/generated/` directory
- Browser console for errors
- Network tab for failed requests

**Solution:**
- Clear browser cache
- Check file permissions
- Verify PDF files exist

### Problem: Timer not working

**Check:**
- Is JavaScript enabled?
- Check browser console for errors
- Verify `/start-session` endpoint works

**Solution:**
- Refresh page
- Clear browser cache
- Check backend logs

### Problem: Answers not saving

**Check:**
- Browser console for errors
- Network tab for failed requests
- Backend logs

**Solution:**
- Check `/save-answers` endpoint
- Verify CSV file permissions
- Check disk space

---

## Next Steps

### For Beginners

1. **Try it locally:**
   ```bash
   ./run.sh
   ```

2. **Create a test exam:**
   - Enter 2-3 simple questions
   - Test as a student
   - Check grading

3. **Deploy to Railway:**
   - Follow [DEPLOYMENT.md](./DEPLOYMENT.md)
   - Get a public URL
   - Share with others

### For Advanced Users

1. **Customize the template:**
   - Edit `templates/snippet_template.tex`
   - Change fonts, sizes, layout

2. **Add features:**
   - Database integration
   - User authentication
   - Advanced analytics

3. **Optimize:**
   - Caching
   - CDN for PDFs
   - Load balancing

### Learning Resources

- **LaTeX:** [Overleaf Learn LaTeX](https://www.overleaf.com/learn)
- **Flask:** [Flask Documentation](https://flask.palletsprojects.com/)
- **Docker:** [Docker Getting Started](https://docs.docker.com/get-started/)
- **Bengali LaTeX:** See `README.md` in this project

---

## Common Questions

### Q: Why LaTeX instead of a simple form?

**A:** LaTeX allows complex mathematical notation, proper formatting, and professional-looking PDFs that are essential for math/science exams.

### Q: Can I use this without Docker?

**A:** Yes, but you need to install TeX Live, Python, and all dependencies manually. Docker makes it much easier.

### Q: Is this secure for production?

**A:** For basic use, yes. For production with sensitive data, consider:
- Adding authentication
- Using HTTPS (automatic on deployment platforms)
- Database instead of CSV files
- Rate limiting

### Q: Can I customize the timer duration?

**A:** Yes! Edit `web/templates/output.html` and change `25` minutes to your desired duration.

### Q: How do I backup student answers?

**A:** The CSV files in `web/answers/` contain all student data. Copy these files regularly.

### Q: Can I add more languages?

**A:** Yes! LaTeX supports many languages. Edit the template and add appropriate fonts.

---

## Summary

This project is a complete MCQ exam system that:

✅ **Allows teachers** to create exams using LaTeX  
✅ **Generates PDFs** automatically  
✅ **Provides a web interface** for students  
✅ **Grades automatically** using answer keys  
✅ **Works on mobile** devices  
✅ **Deploys easily** to free hosting platforms  
✅ **Saves progress** if students refresh the page  

**Everything is ready to use!** Just run `./run.sh` and start creating exams.

---

## Getting Help

- 📖 Check [QUICKSTART.md](./QUICKSTART.md) for quick setup
- 📖 See [DEPLOYMENT.md](./DEPLOYMENT.md) for deployment help
- 📖 Read [DOCKER_SETUP.md](./DOCKER_SETUP.md) for Docker setup
- 📖 Review [SETUP_SUMMARY.md](./SETUP_SUMMARY.md) for best practices

---

**Happy Exam Creating! 🎓**

