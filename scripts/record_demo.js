/**
 * VisionOps End-to-End Demo Recorder
 * Records app workflow with Puppeteer and builds an optimized GIF demo.
 */
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const FRAMES_DIR = '/tmp/visionops_frames';
const OUTPUT_GIF = path.join(__dirname, '../assets/demo.gif');

async function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

async function record() {
  if (fs.existsSync(FRAMES_DIR)) {
    fs.rmSync(FRAMES_DIR, { recursive: true, force: true });
  }
  fs.mkdirSync(FRAMES_DIR, { recursive: true });

  console.log('Launching browser...');
  const browser = await puppeteer.launch({
    headless: 'new',
    executablePath: '/usr/bin/google-chrome',
    args: [
      '--no-sandbox',
      '--disable-setuid-sandbox',
      '--disable-dev-shm-usage',
      '--disable-gpu',
      '--window-size=1440,900',
    ],
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900, deviceScaleFactor: 1 });

  let frameIndex = 0;
  async function capture(count = 1) {
    for (let i = 0; i < count; i++) {
      const framePath = path.join(
        FRAMES_DIR,
        `frame_${String(frameIndex).padStart(5, '0')}.png`
      );
      await page.screenshot({ path: framePath });
      frameIndex++;
    }
  }

  console.log('Navigating to http://localhost:3000 ...');
  await page.goto('http://localhost:3000', { waitUntil: 'networkidle0' });
  await sleep(1000);

  // 1. Initial State
  console.log('Step 1: Capturing Initial State...');
  await capture(10); // ~1 sec

  // 2. Click "Use Sample: 9_Profiling.pdf"
  console.log('Step 2: Clicking Use Sample...');
  const buttons = await page.$$('button');
  let sampleBtn = null;
  for (const b of buttons) {
    const text = await page.evaluate((el) => el.textContent, b);
    if (text && text.includes('Use Sample')) {
      sampleBtn = b;
      break;
    }
  }

  if (sampleBtn) {
    await sampleBtn.hover();
    await capture(4);
    await sampleBtn.click();
    await sleep(800);
    await capture(8); // Show sample loaded
  }

  // 3. Click "Analyze Document"
  console.log('Step 3: Clicking Analyze Document...');
  const buttons2 = await page.$$('button');
  let analyzeBtn = null;
  for (const b of buttons2) {
    const text = await page.evaluate((el) => el.textContent, b);
    if (text && text.includes('Analyze Document')) {
      analyzeBtn = b;
      break;
    }
  }

  if (analyzeBtn) {
    await analyzeBtn.hover();
    await capture(4);
    await analyzeBtn.click();
    await sleep(500);
    await capture(6);
  }

  // 4. Capture Agent Graph Execution Trace in real time
  console.log('Step 4: Monitoring Agent Reasoning & vLLM stream...');
  const startTime = Date.now();
  let completed = false;

  while (!completed && Date.now() - startTime < 120000) {
    await sleep(500);
    await capture(1);

    const statusText = await page.evaluate(() =>
      document.body ? document.body.innerText : ''
    );
    if (
      statusText.includes('Analysis completed successfully') ||
      statusText.includes('Analysis completed') ||
      statusText.includes('Analysis failed')
    ) {
      console.log('Agent run completed. Waiting for diagram SVG to load...');
      completed = true;
    }
  }

  // Wait for SVG fetch to render in DOM
  await sleep(2500);
  console.log('Step 5: Capturing Rendered Architecture Diagram...');
  await capture(15); // ~1.5 sec on complete diagram

  // 5. Scroll smoothly to view Extracted Components and Real Project Context Breakdown
  console.log('Step 6: Scrolling to view Components & Explanation...');
  const scrollSteps = 12;
  const targetScrollY = 820;
  for (let s = 1; s <= scrollSteps; s++) {
    await page.evaluate((y) => {
      window.scrollTo(0, y);
    }, (s / scrollSteps) * targetScrollY);
    await sleep(80);
    await capture(1);
  }

  // Hold on explanation section
  await sleep(2000);
  await capture(20); // ~2 sec on explanation

  // Scroll back to top
  console.log('Step 7: Scrolling back to top...');
  for (let s = 1; s <= scrollSteps; s++) {
    await page.evaluate((y) => {
      window.scrollTo(0, y);
    }, (1 - s / scrollSteps) * targetScrollY);
    await sleep(70);
    await capture(1);
  }

  // Hold final dashboard view
  await sleep(1500);
  await capture(15);

  console.log(`Captured ${frameIndex} frames.`);
  await browser.close();

  // 6. Build optimized GIF using ffmpeg
  console.log('Building optimized GIF with ffmpeg...');
  fs.mkdirSync(path.dirname(OUTPUT_GIF), { recursive: true });

  const ffmpegCmd = `ffmpeg -y -framerate 10 -i ${FRAMES_DIR}/frame_%05d.png -vf "fps=10,scale=1280:-1:flags=lanczos,split[s0][s1];[s0]palettegen=max_colors=128:reserve_transparent=0[p];[s1][p]paletteuse=dither=bayer:bayer_scale=3" "${OUTPUT_GIF}"`;
  console.log('Running:', ffmpegCmd);
  execSync(ffmpegCmd, { stdio: 'inherit' });

  const stats = fs.statSync(OUTPUT_GIF);
  const sizeMb = (stats.size / (1024 * 1024)).toFixed(2);
  console.log(`GIF successfully generated at ${OUTPUT_GIF} (${sizeMb} MB)`);
}

record().catch((err) => {
  console.error('Recording failed:', err);
  process.exit(1);
});
