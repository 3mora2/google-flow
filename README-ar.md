# واجهة برمجية Flow Image المحلية والـ SDK البرمجي (الموحد)

[![PyPI Version](https://img.shields.io/pypi/v/google-flow.svg)](https://pypi.org/project/google-flow/)
[![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](./LICENSE)

النسخة الإنجليزية: [README.md](./README.md) | تفاصيل المعمارية: [ARCHITECTURE-ar.md](./ARCHITECTURE-ar.md)

يوفر هذا المستودع بيئة تشغيل محلية موحدة لتوليد الصور عبر Google Flow، وتوفيرها للبرامج الخارجية كـ **واجهة برمجية (API) متوافقة مع معايير OpenAI**، بالإضافة إلى **مكتبة استدعاء برمجية عالية المستوى لـ Python (FlowSDK)**.

---

## 🌟 الميزات الرئيسية

1. **إعداد موجه وسهل (`/setup`)**: واجهة ويب تفتح تلقائياً لتوجيه المستخدم، وتقوم بالكشف عن حالة تسجيل الدخول تلقائياً ومزامنة الرموز (Tokens) دون الحاجة لنسخها ولصقها يدوياً.
2. **محدث توكنات خلفي (Token Updater)**: خدمة جدولة تعمل في الخلفية للحفاظ على جلسات الحسابات المتعددة نشطة تلقائياً، مع دعم استخدام بروكسي (Proxy) منفصل لكل حساب لعزل البصمة الرقمية.
3. **محلل كابتشا داخلي (In-Process Captcha Solver)**: يحل تحديات الكابتشا (reCAPTCHA) داخل نفس عملية التطبيق عبر Playwright/nodriver، مما يلغي الحاجة لتشغيل خوادم وسيطة أو منافذ شبكة منفصلة.
4. **SDK برمجي للدمج (`FlowSDK`)**: فئة برمجية بايثون آمنة ومتطابقة مع الخيوط المتعددة (Thread-safe) لتضمين توليد الصور مباشرة في تطبيقاتك الخاصة.
5. **توافق كامل مع OpenAI**: يمكنك ربطه بأي تطبيق خارجي لتوليد الصور (مثل Cherry Studio أو Next Chat) عبر إعداد الرابط ومفتاح API واسم النموذج المعروض في واجهة الإعداد.

---

## 🚀 البداية السريعة

### 1. التثبيت والإعداد

اختر إحدى طرق التثبيت التالية:

#### 📦 الطريقة أ: التثبيت عبر PyPI (موصى به لاستخدام الـ SDK والـ CLI العام)
هذه هي الطريقة الأسهل لاستخدام المكتبة برمجياً أو تشغيل خادم الواجهة البرمجية والأوامر بشكل عام:
```bash
pip install google-flow
```
بمجرد التثبيت، يمكنك تشغيل الأوامر مباشرة من الطرفية (Terminal):
* **تشغيل خادم الواجهة البرمجية (API)**: `google-flow-api`
* **تشغيل واجهة سطر الأوامر (CLI)**: `google-flow --help`

#### 🛠️ الطريقة ب: التثبيت المحلي والتطوير (موصى به للمطورين)
إذا كنت تريد تشغيل الخادم محلياً مع بيئة افتراضية مخصصة وسكريبتات تشغيل سريعة:
1. قم بنسخ المستودع والدخول إلى المجلد.
2. انقر نقراً مزدوجاً على ملف التثبيت:
   ```bat
   install.bat
   ```
   *سيقوم هذا الملف بتهيئة البيئة الافتراضية `.venv` وتثبيت الحزم المطلوبة بصيغة القابلة للتعديل وتنزيل متصفح Playwright Chromium تلقائياً.*

### 2. التشغيل

انقر نقراً مزدوجاً على ملف التشغيل:
```bat
start-flow-api.bat
```
*سيقوم ببدء تشغيل خادم الويب على المنفذ `8787` وفتح صفحة الإعداد تلقائياً في المتصفح.*

### 3. إكمال الإعداد
1. سجل الدخول إلى حساب جوجل الخاص بك على موقع Google Flow في نافذة المتصفح المفتوحة.
2. انتظر حتى تتعرف صفحة الإعداد (`http://127.0.0.1:8787/setup`) على نجاح الدخول تلقائياً.
3. انسخ الرابط، ومفتاح API، واسم النموذج المعروض في النهاية لاستخدامه في برامجك.

---

## 📡 مرجع الواجهة البرمجية (API Reference)

### تفاصيل الاتصال الافتراضية
* **الرابط الأساسي**: `http://127.0.0.1:8787/v1`
* **مفتاح الـ API الافتراضي**: `flow-local-key`

### نقاط النهاية (Endpoints)
* `POST /v1/images/generations` - توليد الصور من نصوص (Text-to-Image)
* `POST /v1/images/edits` - توليد الصور من صور (Image-to-Image)
* `GET /v1/models` - سرد قائمة النماذج والنسب المدعومة
* `GET /health` - التحقق من سلامة الخدمة
* `GET /setup` - معالج الإعداد التلقائي

---

## 🐍 دليل استخدام مكتبة بايثون (FlowSDK)

يمكنك استيراد المكتبة مباشرة داخل كود بايثون الخاص بك كالتالي:

```python
import asyncio
from google_flow import FlowSDK

async def main():
    # الخيار 1: تجاوز الجلسة يدوياً بتوكن اتصال مباشر
    async with FlowSDK(st_token="your-session-token", project_id="your-project-id") as sdk:
        image_path = await sdk.generate(
            prompt="A futuristic city in antigravity, neon lights, 4k",
            model="gemini-3.1-flash-image-landscape",
            output_path="output/direct_t2i.png"
        )
        print(f"تم حفظ الصورة في: {image_path}")

    # الخيار 2: الاختيار التلقائي للحساب (يستخرج التوكن والبروكسي تلقائياً من قاعدة بيانات SQLite)
    async with FlowSDK() as sdk:
        await sdk.select_profile("My_Google_Profile_Name")
        image_path = await sdk.generate(
            prompt="A majestic golden eagle flying over mountains",
            model="gemini-3.1-flash-image-square",
            output_path="output/profile_t2i.png"
        )
        print(f"تم حفظ الصورة في: {image_path}")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 📁 هيكلية المستودع

```text
flow-image-cli-local-api/
├── google_flow/              # الحزمة الأساسية الموحدة للمشروع
│   ├── api/               # خادم ويب FastAPI ولوحة التحكم الرسومية
│   ├── captcha/           # خطافات حل الكابتشا داخل العملية (In-process)
│   ├── captcha_service/   # محرك حل الكابتشا (nodriver/playwright)
│   ├── token_updater/     # خدمة تحديث ومراقبة الجلسات التلقائية
│   ├── core/              # فئة الـ SDK والعميل البرمجي (FlowSDK)
│   └── utils/             # أدوات التحليل المشتركة والبروكسي وقواعد البيانات
├── examples/              # أمثلة استدعاء برمجية جاهزة للتشغيل
├── release-package/       # أدوات بناء حزم التوزيع النظيفة للمستخدم النهائي
├── install.bat            # سكريبت التثبيت بنقرة واحدة لويندوز
├── start-flow-api.bat     # سكريبت بدء التشغيل بنقرة واحدة لويندوز
├── API_USAGE.md           # أمثلة cURL وطلبات الـ API المتوافقة
└── README-ar.md           # هذا الملف التوضيحي باللغة العربية
```

## 📦 بناء حزمة النشر والتوزيع (Release)

لمشاركة نسخة نظيفة خالية من مجلدات التطوير (مثل `.git` و `.venv` ومجلدات المخرجات المؤقتة):
1. قم بتشغيل سكريبت البناء: `release-package\build-release-package.bat`
2. ستجد الملف المضغوط جاهزاً للتوزيع في المسار التالي: `release-package\dist\flow-image-cli-local-api-v1.0.0.zip`

## 📝 الترخيص

هذا المشروع مرخص بموجب ترخيص MIT.
