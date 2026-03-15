# Termux Video Downloader (ytdl)

Termux ke liye ek super fast, powerful aur bahut hi sundar video downloader! 🚀
Is script ki madad se aap YouTube, Instagram, Facebook, aur aisi hi saikdon aur sites se seedhe apne phone me videos aur audio download kar sakte hain.

> **💡 Note for Beginners:** Agar aap Termux pehli baar use kar rahe hain aur aapne kabhi Linux use nahi kiya hai, toh ghabrane ki zarurat nahi hai! Bas in steps ko bilkul waise hi follow karein jaise niche likha hai.

---

## 🛠️ Step 1: Termux Setup aur Zaroori Tools (Pehle ye karein!)

Pehle hum apne Termux ko storage ki permission denge aur git jaisi zaruri cheezein install karenge.

1. **Termux app open karein.**
2. Niche diye gaye command ko copy karein aur Termux me paste karke **Enter** dabayein:
   ```bash
   termux-setup-storage
   ```
   *Aapke phone me storage permission mangne ke liye ek popup aayega. Usme **Allow** par tap karein.*
3. Ek baar phir se yahi command chalayein:
   ```bash
   termux-setup-storage
   ```
   *Agar confirm karne ko pooche, toh `y` likhkar Enter daba dein.*

4. **Ab Termux ko update karein aur zaroori dependencies install karein (isme thoda time lag sakta hai, poora hone dein):**
   ```bash
   pkg update -y && pkg upgrade -y && pkg install python3 ffmpeg aria2 git python3-venv -y
   ```

---

## ⚙️ Step 2: Python Virtual Environment Banana

Pehle hum Termux ki home directory me ek virtual environment banayenge:

1. Wapas home screen pe aane ke liye:
   ```bash
   cd ~
   ```
2. Virtual environment banayein:
   ```bash
   python3 -m venv venv
   ```

---

## 📂 Step 3: Folder Banana aur Script Download (Clone) Karna

Hume downloader ko aapke phone ke internal Download folder me rakhna hai.

1. Apne phone ke internal storage path par jane ke liye yeh type karein:
   ```bash
   cd storage/emulated/0/Download
   ```
   *(🚨 **Agar upar wala command error de, toh yeh try karein:** `cd storage/downloads`)*

2. Ek naya folder banayein aur uske andar jayein:
   ```bash
   mkdir termux 
   cd termux
   ```

3. **Ab downloader script ko wahan download (clone) karein:**
   *(Kyunki humne Step 1 me Git install kar liya tha, ab yeh error nahi dega)*
   ```bash
   git clone https://github.com/YOUR_GITHUB_USERNAME/ytdl.git
   ```

---

## 🔗 Step 4: Shortcut (Alias) Banana

Baar-baar lambe commands type na karne padein, isliye hum `.bashrc` file me shortcut set karenge.

1. `.bashrc` file ko edit karne ke liye open karein:
   ```bash
   nano ~/.bashrc
   ```

2. **Ab is file me niche diya gaya text paste karein.** Dhyan dein, wahi wala hissa paste karein jo path aapke phone me Step 3 me kaam kiya tha:

   **👉 1. Agar `cd storage/emulated/0/Download` command kaam kiya tha:**
   ```bash
   alias pyd="cd storage/emulated/0/Download && ~/venv/bin/python termux/ytdl/ytdl-1.py"
   alias ins="~/venv/bin/pip install -r storage/emulated/0/Download/termux/ytdl/requirements.txt"
   ```

   **👉 2. Agar `cd storage/downloads` command kaam kiya tha:**
   ```bash
   alias pyd="cd storage/downloads && ~/venv/bin/python termux/ytdl/ytdl-1.py"
   alias ins="~/venv/bin/pip install -r storage/downloads/termux/ytdl/requirements.txt"
   ```

3. **File ko save karne ke liye Termux ke extra keys (Ctrl) ka use karein:**
   - Screen par dikh rahe **Ctrl** button ko touch karein.
   - Keyboard me **o** (alphabet O) press karein aur **Enter** button dabayein.
   - Fir se **Ctrl** touch karein aur keyboard par **x** press karein (is se nano editor se bahar aa jayenge).

4. Apne naye shortcuts ko activate karne ke liye akhir me yeh command chalayein:
   ```bash
   source ~/.bashrc
   ```

---

## 📦 Step 5: Requirements Install Karna

Jo shortcut (`ins`) humne upar banaya hai, uska use karke zaroori python packages install karein (yeh process bas ek baar karna hai):
```bash
ins
```

Ab sab setup bilkul complete ho chuka hai! Aage ka process dekhein videos download karne ke liye.

---

## 🎉 Downloader Kaise Use Karein!

Aap bilkul ready hain! Ab aap videos download karna shuru kar sakte hain. Dhyan rahe ki upar ke saare step poore ho gaye hone chahiye.

*(⚠️ **Zaroori Note:** Is script se kai saare video ek sath (batch download) ya puri playlist download nahi hogi. Yeh ek baar me ek video download karne ke liye hai.)*

### 🎬 Video Download Karna
Kisi ytdlp supported site se video ko download karne ke liye, bas apna naya `pyd` command likhein aur link daalein:

```bash
pyd "YAHAN_APNA_LINK_PASTE_KAREIN"
```

**Example:**
```bash
pyd "https://www.youtube.com/watch?v=VIDEO_ID"
```

* **Iske baad kya hoga?** Script aapko sabhi available qualities (jese 1080p, 720p) ki ek sundar table dikhayegi. Jo format aapko chahiye bas uska **number** type karke Enter dabayein! Video aapke phone ki gallery me save ho jayega.

---
*Created with ❤️ for Termux users.*
