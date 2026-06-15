# واجهة برمجية Flow Image المحلية (Flow Image Local API)

English README: [README.md](./README.md)

يقوم هذا المستودع بتنظيم `flow-image-cli` في إصدار أكثر ملاءمة للنشر المحلي والمشاركة مع الآخرين، ويوفر واجهة برمجية للصور متوافقة مع OpenAI.

خطوات الاستخدام الموصى بها بسيطة للغاية:

1. انقر نقرًا مزدوجًا على `install.bat`
2. انقر نقرًا مزدوجًا على `start-flow-api.bat`
3. سجل الدخول إلى Google Flow في المتصفح الذي يفتح تلقائيًا
4. انتظر حتى تكتمل صفحة `/setup` تلقائيًا، ثم انسخ قيم `URL` و`API Key` و`Model` المعروضة في النهاية.

لا حاجة لإضافات المتصفح.

## ماذا يتضمن هذا الإصدار

- خدمة واجهة برمجية (API) محلية متوافقة مع OpenAI
- صفحة إعداد إرشادية عند `/setup`
- كشف تلقائي لتسجيل الدخول إلى Flow ومزامنة الرموز المميز (Tokens)
- توليد الصور من نص (Text-to-Image) وتوليد الصور من صور (Image-to-Image)
- خيارات دقة الإخراج: 1K / 2K / 4K
- تخطيط الأبعاد والنسب لـ `1:1` و`9:16` و`16:9` و`21:9`
- تدفق معالجة الكابتشا وتسجيل الدخول عبر متصفح محلي يعتمد على Playwright

## متطلبات التشغيل

- نظام التشغيل Windows
- إصدار Python 3.10 أو أحدث
- إمكانية الوصول وتسجيل الدخول إلى Flow: <https://labs.google/fx>
- حساب جوجل يمتلك صلاحية توليد الصور على Flow بالفعل

## البداية السريعة

### 1. التثبيت

انقر نقرًا مزدوجًا على:

```bat
install.bat
```

سيقوم تلقائيًا بـ:

- إنشاء البيئة الافتراضية `.venv`
- تثبيت مكتبات Python المطلوبة
- تثبيت المشروع في وضع القابلية للتعديل (Editable mode)
- تثبيت متصفح Playwright Chromium

### 2. التشغيل

انقر نقرًا مزدوجًا على:

```bat
start-flow-api.bat
```

بعد التشغيل، سيفتح تلقائيًا:

- صفحة الإعداد: `http://127.0.0.1:8787/setup`
- عنوان الـ API: `http://127.0.0.1:8787/v1`

### 3. إكمال الإعداد

في صفحة الإعداد:

1. سجل الدخول إلى Google Flow باتباع التعليمات
2. انتظر حتى يكتشف النظام حالة تسجيل الدخول تلقائيًا
3. دع الخدمة المحلية تكمل المزامنة تلقائيًا
4. انسخ معلومات الـ API مباشرة من بطاقة المعلومات المعروضة

توفر صفحة الإعداد:

- `Open Login` (فتح تسجيل الدخول)
- `Re-sync` (إعادة المزامنة)
- `Reset Config` (إعادة تعيين الإعدادات)
- بطاقات معلومات API سهلة القراءة بدلاً من عرض الـ JSON الخام

## معلومات الـ API الافتراضية

الإعدادات المحلية الافتراضية كالتالي:

- الرابط الأساسي (Base URL): `http://127.0.0.1:8787/v1`
- مفتاح API: `flow-local-key`

إذا كنت ترغب في تغيير مفتاح API، يمكنك تعيينه قبل التشغيل عبر:

```powershell
$env:FLOW_API_KEY="your-own-key"
```

## الواجهات المدعومة (Endpoints)

- `GET /health`
- `GET /setup`
- `GET /setup/status`
- `POST /setup/open-login`
- `POST /setup/finalize`
- `POST /setup/reset`
- `GET /v1/models`
- `POST /v1/images/generations`
- `POST /v1/images/edits`
- `POST /v1/chat/completions`
- `GET /v1/files/{filename}`

## استخدام النماذج

أمثلة لمعرفات النماذج (Model IDs) التي يمكن استخدامها مباشرة:

- `gemini-3.1-flash-image-landscape`
- `gemini-3.1-flash-image-portrait`
- `gemini-3.1-flash-image-square`
- `gemini-3.0-pro-image-landscape`
- `imagen-4.0-generate-preview-landscape`
- `nano-banana-2-landscape`
- `nano-banana-2-portrait`
- `nano-banana-2-square`
- `nano-banana-2-ultrawide`
- `nano-banana-pro-landscape`
- `nano-banana-pro-portrait`
- `nano-banana-pro-square`

تدعم أيضاً الأسماء المستعارة لعائلات النماذج:

- `gemini-3.1-flash-image`
- `gemini-3.0-pro-image`
- `imagen-4.0-generate-preview`
- `nano banana2`
- `nano banana pro`

ملاحظة خاصة:

- يدعم نموذج `nano banana2` فقط الأبعاد بنسبة `21:9`

## تخطيط الأحجام والنسب

لتسهيل استدعاء الطرف الثالث، تدعم طبقة التوافق هذه حقول الحجم الشائعة وتلميحات أكثر سهولة.

تخطيط الأحجام:

- `1K` -> الصورة الأصلية
- `2K` -> تكبير بدقة 2K
- `4K` -> تكبير بدقة 4K
- `1024x1024` -> صورة مربعة
- `1024x1536` -> صورة عمودية
- `1536x1024` -> صورة أفقية

تخطيط النسب والأبعاد:

- `1:1` -> صورة مربعة
- `9:16` -> صورة عمودية
- `16:9` -> صورة أفقية
- `21:9` -> صورة عريضة جداً (فقط مع `nano banana2`)

تخطيط الجودة:

- `standard` -> الصورة الأصلية
- `hd` أو `2k` -> تكبير بدقة 2K
- `4k` -> تكبير بدقة 4K

يمكن للنظام أيضاً التعرف على التلميحات المضمنة في الوصف النصي (Prompt)، مثل:

- `Preferred size: 4K`
- `Preferred aspect ratio: 9:16`

## أمثلة على الطلبات

توليد صورة من نص (Text-to-Image):

```bash
curl http://127.0.0.1:8787/v1/images/generations ^
  -H "Authorization: Bearer flow-local-key" ^
  -H "Content-Type: application/json" ^
  -d "{\"model\":\"gemini-3.1-flash-image\",\"prompt\":\"a cinematic cat\",\"size\":\"1536x1024\",\"quality\":\"hd\",\"response_format\":\"url\"}"
```

توليد صورة من صورة (Image-to-Image):

```bash
curl http://127.0.0.1:8787/v1/images/edits ^
  -H "Authorization: Bearer flow-local-key" ^
  -F "model=gemini-3.1-flash-image" ^
  -F "prompt=convert to watercolor" ^
  -F "size=1024x1024" ^
  -F "quality=2k" ^
  -F "image=@input.jpg"
```

مثال على الاستدعاء باستخدام لغة Python:

```python
import asyncio
from flow_cli import FlowSDK

async def main():
    # استخدام FlowSDK برمجياً داخل كودك الخاص
    async with FlowSDK(st_token="your-session-token-here") as sdk:
        path = await sdk.generate(
            prompt="a cinematic cat",
            model="gemini-3.1-flash-image-landscape",
            output_path="output/api_basic.png",
        )
        print(f"Saved to: {path}")

asyncio.run(main())
```

لمزيد من أمثلة الاستدعاء، راجع ملف [API_USAGE.md](./API_USAGE.md).

## هيكلية المستودع

```text
flow-image-cli/
├── flow_cli/              # خدمات الـ API المحلية والـ CLI الأساسي
├── install.bat            # التثبيت بنقرة واحدة
├── start-flow-api.bat     # التشغيل بنقرة واحدة
├── API_USAGE.md           # أمثلة واجهة برمجية متوافقة
└── README.md
```

## ملاحظات هامّة

- يستهدف هذا المستودع عمليات النشر المحلية على جهازك الخاص أو أي كمبيوتر آخر يعمل بنظام التشغيل Windows.
- يحتاج المستخدم فقط إلى إكمال تسجيل الدخول إلى Google Flow.
- يتم إكمال بقية الإعدادات والمزامنة تلقائيًا بواسطة الخدمة المحلية.
- إذا كان الحساب نفسه لا يمتلك صلاحية توليد الصور على Flow أو صلاحية 4K، فستظل الطلبات مقيدة من قبل الخدمة الرئيسية.

## License

MIT
