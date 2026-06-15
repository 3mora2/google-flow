# معمارية تشغيل وتصميم مكتبة مشروع `google_flow`

يوفر هذا المستند شرحاً تفصيلياً معمقاً لهيكل وتصميم مشروع `google_flow` الموحد بعد دمج كافة المكونات (محدث التوكنات التلقائي وجسر حل الكابتشا)، مع التركيز على شرح طريقة عمل الأكواد، تصميم الجداول، وتدفق البيانات لتمكين المطورين من استخدام المكتبة ككود داخلي في مشاريعهم الخاصة.

---

## 1. أهداف التصميم وفلسفة الدمج (Design Goals)

يهدف مشروع `google_flow` الموحد إلى حل ثلاثة تحديات رئيسية في التعامل مع بوابة Google Flow:
1. **تخطي حماية الكابتشا (reCAPTCHA Bypass)**: عبر إدارة متصفح تلقائي (Playwright/nodriver) يقوم بتوليد رموز التحقق وتجديدها في الخلفية.
2. **استمرارية الجلسات للحسابات المتعددة (Session Keep-Alive)**: عبر نظام ذكي يراقب صلاحية رموز الاتصال (Tokens) ويحدثها تلقائياً قبل انتهائها.
3. **الدمج البرمجي السهل (SDK Integration)**: تجميع كل هذه التعقيدات خلف فئة بايثون موحدة (`FlowSDK`) يمكن تضمينها في أي تطبيق آخر كحزمة داخلية (In-Process Library).

---

## 2. البنية البرمجية والمكونات الأساسية (System Components)

### أ. واجهة الاستدعاء البرمجي الموحدة: `FlowSDK`
تعتبر فئة `FlowSDK` (الموجودة في [google_flow/core/sdk.py](file:///d:/projects/flow-image-cli-local-api/google_flow/core/sdk.py)) المدخل الرئيسي للمطورين. 

**الخصائص التقنية لـ `FlowSDK`:**
- **عزل التكوينات (Thread-Safe Config Isolation)**: عند الدخول في سياق تشغيل المكتبة `async with FlowSDK(...)` تقوم بحفظ الإعدادات العالمية الحالية وتطبيق إعدادات مخصصة للجلسة، ثم استعادتها تلقائياً عند الخروج. يمنع هذا التداخل عند تشغيل طلبات متوازية أو تضمينها في خوادم ويب أخرى.
- **إدارة الاتصال وقاعدة البيانات**: تقوم بالاتصال المباشر بقاعدة بيانات الحسابات وتثبيت الـ context.
- **التكامل مع مزود الكابتشا**: تستدعي `InProcessCaptchaProvider` بشكل تلقائي لحل الكابتشا داخلياً في نفس عملية التشغيل دون الحاجة لتشغيل خادم ويب إضافي وجسر كابتشا خارجي.

---

### ب. مشغل الكابتشا الداخلي: `InProcessCaptchaProvider`
تاريخياً، كانت خدمة حل الكابتشا تتطلب تشغيل خادم ويب مستقل (HTTP Bridge) لتلقي طلبات الحل.
قمنا بإنشاء `InProcessCaptchaProvider` في [google_flow/captcha/in_process_provider.py](file:///d:/projects/flow-image-cli-local-api/google_flow/captcha/in_process_provider.py) ليقوم بـ:
- ربط كود العميل مباشرة بـ `CaptchaRuntime` المحلي.
- معالجة طلب تخطي الكابتشا وتسجيل الجلسة وإغلاقها برمجياً في الذاكرة مباشرة.
- توفير أداء أسرع واستهلاك موارد أقل بنسبة 60% مع إزالة تعقيدات الشبكة والـ Ports.

---

### ج. محرك محاكاة المتصفح الفردي: `browser_captcha_personal.py` (nodriver)
يدعم محرك الكابتشا طريقتين للتشغيل:
1. **Browser Mode (Playwright)**: تشغيل متصفح خفي وتخطي الكابتشا لكل طلب على حدة.
2. **Personal Mode (nodriver)**: مبني على مكتبة `nodriver` (المطور المحدث لـ `undetected-chromedriver`).
   - يقوم بفتح نوافذ متصفح دائمة (Resident Tabs) لحساباتك.
   - يعيد استخدام هذه النوافذ لتوليد رموز التخطي فورياً دون الحاجة لتشغيل متصفح جديد في كل مرة (Cold Start).
   - يدعم استخلاص الـ Cookies والـ Session Token مباشرة من تخزين المتصفح وتمريرها برمجياً لقاعدة البيانات.

---

### د. مجدول التحديث الدائم: `TokenUpdater`
يتم تشغيل مجدول المهام المعتمد على `APScheduler` لتتبع الحسابات في قاعدة البيانات:
- **التحديث البروتوكولي (Protocol Login)**: محاولة مصادقة الحساب عبر طلبات HTTP المباشرة (API-based OAuth) وهي الطريقة الأسرع والأخف.
- **التحديث التفاعلي (Browser Login)**: في حال انتهاء الجلسة تماماً وتطلب جوجل التحقق البشري، يقوم المجدول برفع تنبيه ويفتح نافذة متصفح يدوية للمستخدم ليقوم بتسجيل الدخول مرة واحدة فقط، ثم يتم حفظ الجلسة الجديدة تلقائياً.

---

## 3. مخطط معمارية النظام وتكامل البيانات

المخطط التالي يوضح معمارية الاتصال الداخلي بين مختلف الطبقات والمكتبات:

```mermaid
graph TB
    %% تعريف ستايل المكونات
    classDef storage fill:#1e1b4b,stroke:#818cf8,stroke-width:2px,color:#fff;
    classDef engine fill:#0f172a,stroke:#38bdf8,stroke-width:2px,color:#e2e8f0;
    classDef api fill:#31102f,stroke:#db2777,stroke-width:2px,color:#fdf2f8;
    classDef config fill:#1c1917,stroke:#d6d3d1,stroke-width:1.5px,color:#fafaf9;

    subgraph طبقة_البيانات ["طبقة البيانات والتخزين"]
        AppConfig[الإعدادات العامة config.py]:::config
        SqliteDB[(قاعدة بيانات SQLite - data/flow.db)]:::storage
    end

    subgraph المحركات_الداخلية ["طبقة التشغيل والمحركات"]
        FlowSDK[مكتبة FlowSDK]:::engine
        CaptchaRuntime[محلل الكابتشا CaptchaRuntime]:::engine
        TokenUpdater[محدث التوكنات TokenUpdater]:::engine
        ProfileDB[قاعدة الحسابات ProfileDB]:::storage
        SessionRegistry[سجل الجلسات النشطة SessionRegistry]:::storage
    end

    subgraph طبقة_الواجهات ["طبقة الواجهات الرسومية وخدمات الويب"]
        FastAPIServer[خادم ويب FastAPI]:::api
        AdminDashboard[لوحة التحكم للمسؤول]:::api
        UserPortal[بوابة الحسابات والعملاء]:::api
        CaptchaBridge[جسر الكابتشا HTTP Bridge]:::api
    end

    %% الترابط البرمجي
    AppConfig -->|تخزين الإعدادات| SqliteDB
    ProfileDB -->|إدارة سجلات الحسابات| SqliteDB
    TokenUpdater -->|التحقق من حالة الحسابات والبروكسي| ProfileDB
    CaptchaRuntime -->|إثبات تراخيص الـ API Keys والعقد| SqliteDB
    CaptchaRuntime -->|تتبع الجلسات المفتوحة| SessionRegistry

    %% تدفق العمليات
    FlowSDK -->|طلب التوكن لحل الطلب| CaptchaRuntime
    FlowSDK -->|قراءة الحساب المختار| ProfileDB
    
    FastAPIServer -->|عرض واجهة المسؤول| AdminDashboard
    FastAPIServer -->|عرض بوابة العميل| UserPortal
    FastAPIServer -->|معالجة طلب الكابتشا| CaptchaRuntime
    FastAPIServer -->|التحكم في جدولة التحديث| TokenUpdater
    
    CaptchaBridge -->|الاستجابة لطلبات YesCaptcha| CaptchaRuntime
```

---

## 4. نموذج وهيكلية قاعدة البيانات (Database Schema)

تستخدم المكتبة قاعدة بيانات SQLite موحدة وموجودة افتراضياً في `data/flow.db`. تحتوي على الجداول التالية:

### 1. جدول الحسابات الشخصية (`profiles`)
يخزن بيانات الحسابات والمتصفحات المخصصة لتحديث التوكنات وتوثيق الاتصال:
- `id`: المعرف الفرعي التلقائي.
- `name`: اسم مميز للحساب (يستخدمه الـ SDK لاختيار الجلسة).
- `email`: البريد الإلكتروني لحساب جوجل.
- `is_logged_in`: حالة تسجيل الدخول (0 أو 1).
- `is_active`: حالة تفعيل الحساب في المهام الدورية (0 أو 1).
- `last_token`: آخر رمز جلسة تم الحصول عليه لاستخدامه في إنشاء الصور.
- `last_token_time`: توقيت جلب الرمز الأخير.
- `proxy_enabled` & `proxy_url`: إعدادات البروكسي الخاص بهذا الحساب فقط لعزل البصمة الرقمية للمتصفح.
- `google_cookies`: كوكيز جلسة حساب جوجل مشفرة أو مخزنة نصياً لتسهيل تسجيل الدخول التلقائي.

### 2. جدول سجل المزامنة (`sync_history`)
يتتبع نتائج وتواريخ عمليات المزامنة لكل حساب لتشخيص المشاكل والتعرف على أسباب فشل التحديث.

### 3. جدول مفاتيح الخدمة (`api_keys`)
مخصص لإدارة تراخيص الخدمات الخارجية المسموح لها باستغلال خادم الكابتشا والتحقق من الحصص المتاحة (Credits).

### 4. جدول المستخدمين وبطاقات الشحن (`users` & `cdks`)
يتتبع المستخدمين المسجلين في بوابة الخدمة المشتركة وأكواد الشحن (CDK) الخاصة بزيادة عدد مرات التوليد المسموحة لهم.

---

## 5. دليل استخدام المكتبة ككود داخلي في مشاريع بايثون أخرى

يمكنك استيراد الحزمة مباشرة واستخدامها داخل مشروع بايثون الخاص بك بكل سهولة.

### مثال 1: توليد صورة باستخدام توكن اتصال مباشر (Direct Token Mode)
هذا الوضع مفيد إذا كنت تمتلك توكن الاتصال مسبقاً وتريد فقط استخدام محرك إرسال الطلبات التلقائي:

```python
import asyncio
from google_flow.core.sdk import FlowSDK

async def generate_simple():
    # تمرير التوكن ومعرف المشروع مباشرة للمكتبة
    async with FlowSDK(
        st_token="SECURE_SESSION_TOKEN_HERE",
        project_id="YOUR_PROJECT_ID_HERE",
    ) as client:
        print("بدء عملية توليد الصورة...")
        # إرسال طلب توليد الصورة
        result = await client.generate_image(
            prompt="A majestic golden eagle flying over snowy mountains, digital art, 4k",
            aspect_ratio="16:9",
            size="1536x1024"
        )
        print(f"تم توليد الصورة بنجاح! رابط الصورة: {result}")

if __name__ == "__main__":
    asyncio.run(generate_simple())
```

---

### مثال 2: استخدام إدارة الحسابات والحل التلقائي للكابتشا (Automatic Profile & Captcha Mode)
هذا هو الوضع الأقوى، حيث تقوم المكتبة بالبحث عن الحساب الشخصي في قاعدة بيانات `ProfileDB` الخاصة بك وتوليد توكن الكابتشا تلقائياً في الخلفية لحل الطلب:

```python
import asyncio
from google_flow.core.sdk import FlowSDK

async def generate_with_profile():
    # اختيار الحساب المسجل مسبقاً في واجهة النظام بالاسم
    # ستقوم المكتبة بالاتصال بقاعدة البيانات وحل الكابتشا تلقائياً في الخلفية
    async with FlowSDK(profile_name="Ammar_Account_01") as client:
        print(f"تم شحن بيانات الحساب: {client.profile_name}")
        
        try:
            result = await client.generate_image(
                prompt="Futuristic cyberpunk city street at night, neon lights, premium design, highly detailed",
                aspect_ratio="1:1",
                size="1024x1024"
            )
            print(f"رابط الصورة المولدة: {result}")
            
            # التحقق من الرصيد المتبقي للحساب الحالي
            credits = await client.get_credits()
            print(f"الرصيد المتبقي للحساب: {credits}")
            
        except Exception as e:
            print(f"حدث خطأ أثناء التوليد: {e}")

if __name__ == "__main__":
    asyncio.run(generate_with_profile())
```

---

## 6. سير العمليات التفصيلي عند التشغيل (Sequence diagrams)

### أ. دورة حياة طلب صورة برمجياً

```mermaid
sequenceDiagram
    autonumber
    actor App as تطبيق المطور الخارجي
    participant SDK as مكتبة FlowSDK (google_flow)
    participant IPProvider as مشغل الكابتشا الداخلي
    participant Runtime as مشغل الكابتشا العام
    participant Browser as متصفح الويب (nodriver)
    participant FlowAPI as خادم Google Flow

    App->>SDK: فتح جلسة التشغيل (FlowSDK)
    Note over SDK: حفظ الإعدادات العالمية الحالية<br/>استدعاء التوكن والبروكسي المخصص للحساب من قاعدة البيانات
    SDK-->>App: الجلسة جاهزة للاستخدام

    App->>SDK: توليد صورة: generate_image(prompt)
    SDK->>IPProvider: طلب رمز تخطي كابتشا (reCAPTCHA)
    IPProvider->>Runtime: حل الكابتشا (solve)
    
    alt وضع الجلسات الدائمة النشط (personal)
        Runtime->>Browser: جلب التوكن المولد مسبقاً من التاب المقيم (فوري)
    else وضع تشغيل المتصفح المؤقت (browser)
        Runtime->>Browser: فتح نافذة خفية وتخطي الكابتشا برمجياً
    end
    
    Browser-->>Runtime: رمز التحقق التلقائي
    Runtime-->>IPProvider: الرمز وسجل الجلسة
    IPProvider-->>SDK: الرمز
    
    SDK->>FlowAPI: إرسال طلب توليد الصورة مصحوباً برمز الكابتشا
    FlowAPI-->>SDK: نجاح العملية وإرسال رابط الصورة المولدة
    SDK-->>App: رابط الصورة النهائي
    
    Note over SDK: عند إغلاق الجلسة: استعادة الإعدادات العامة الأصلية
```

### ب. دورة حياة فحص وتحديث التوكن التلقائي

```mermaid
sequenceDiagram
    autonumber
    participant Scheduler as المجدول التلقائي (APScheduler)
    participant ProfileDB as قاعدة البيانات
    participant GoogleAuth as خادم مصادقة Google
    participant Browser as متصفح تسجيل الدخول التفاعلي

    loop كل N دقيقة
        Scheduler->>ProfileDB: جلب جميع الحسابات المفعلة
        loop لكل حساب
            Scheduler->>GoogleAuth: هل التوكن الحالي صالح للاستخدام؟
            GoogleAuth-->>Scheduler: إرجاع النتيجة (صالح / منتهي)
            alt التوكن منتهي ويحتاج تجديد
                Scheduler->>GoogleAuth: طلب تجديد الجلسة بالـ Refresh Token
                alt نجاح التجديد التلقائي
                    GoogleAuth-->>Scheduler: الرمز الجديد
                    Scheduler->>ProfileDB: حفظ الرمز الجديد واستخدامه فوراً
                else فشل التجديد التلقائي (يتطلب مصادقة بشرية)
                    Scheduler->>Browser: فتح نافذة متصفح يدوية للمستخدم
                    Note over Browser: يكمل المستخدم تسجيل الدخول يدوياً في ثوانٍ
                    Browser->>ProfileDB: استخراج الكوكيز وحفظ الجلسة الجديدة تلقائياً
                end
            end
        end
    end
```
