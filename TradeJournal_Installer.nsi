; TradeJournal_Installer.nsi
; این یک اسکریپت NSIS برای ساخت فایل نصبی (Installer) برای Trade Journal است.

; --------------------------------------------------------------------------------------
; تنظیمات کلی Installer
; --------------------------------------------------------------------------------------

!define APP_NAME "Trade Journal"
!define COMPANY_NAME "Yousefeshoon Trading" ; نام شرکت/خودت رو اینجا بنویس
; حتماً این ورژن‌ها را با آخرین نسخه در فایل version_info.py و نام فایل‌های exe در پوشه dist مطابقت دهید!
!define VERSION_MAJOR "1"
!define VERSION_MINOR "11"
!define VERSION_PATCH "03" 

; نام فایل اجرایی نصبی که تولید می‌شود
OutFile "TradeJournal_Setup_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe"

; مجوز (License) برنامه (می‌تونی یک فایل license.txt بسازی و اینجا مسیرش رو بدی)
; LicenseData "license.txt" ; اگر فایل مجوز نداری، این خط رو کامنت کن یا حذف کن

; تصویر پس‌زمینه Installer (می‌تونی یک فایل PNG یا BMP برای پس‌زمینه بسازی)
; !define MUI_WELCOMEFINISHPAGE_BITMAP ".\installer_background.bmp"
; !define MUI_UNWELCOMEFINISHPAGE_BITMAP ".\installer_background.bmp"

; آیکون Installer (می‌تونی یک فایل .ico برای آیکون Installer بسازی)
; !define MUI_ICON ".\installer_icon.ico"

; زبان Installer
Unicode True ; برای پشتیبانی از زبان فارسی

; رابط کاربری مدرن NSIS (MUI)
!include "MUI2.nsh"

; --------------------------------------------------------------------------------------
; صفحات رابط کاربری Installer
; --------------------------------------------------------------------------------------

; صفحه خوش‌آمدگویی
!insertmacro MUI_PAGE_WELCOME

; اگر صفحه مجوز را می‌خواهید، باید این خط را Uncomment کنید و فایل license.txt را آماده کنید:
; !insertmacro MUI_PAGE_LICENSE "license.txt" ; مسیر فایل مجوز را اینجا بدهید، مثلا "$NSISDIR\license.txt"

; صفحه انتخاب اجزا (Components Page) - اینجا آپشن‌های نصب را تعریف می‌کنیم
!insertmacro MUI_PAGE_COMPONENTS

; صفحه انتخاب مسیر نصب
!insertmacro MUI_PAGE_DIRECTORY

; صفحه نصب (Installation Page)
!insertmacro MUI_PAGE_INSTFILES

; صفحه پایان نصب
!insertmacro MUI_PAGE_FINISH

; --------------------------------------------------------------------------------------
; صفحات Uninstaller (حذف کننده)
; --------------------------------------------------------------------------------------

; صفحه خوش‌آمدگویی Uninstaller
!insertmacro MUI_UNPAGE_WELCOME

; صفحه Uninstaller (Installation Page)
!insertmacro MUI_UNPAGE_INSTFILES

; صفحه پایان Uninstaller
!insertmacro MUI_UNPAGE_FINISH

; --------------------------------------------------------------------------------------
; بخش‌های نصب (Sections)
; --------------------------------------------------------------------------------------

; بخش اصلی برنامه (همیشه نصب می‌شود)
Section "برنامه اصلی (${APP_NAME})" SecMain
    SetOutPath "$INSTDIR" ; فایل‌ها را در مسیر نصب کپی کن

    ; کپی کردن فایل‌های اصلی برنامه (از پوشه dist)
    ; حتماً نام فایل exe برنامه اصلی را با نام دقیق فعلی در پوشه dist جایگزین کن!
    ; (مثلا: Trade_Journal_v1.00.00.exe)
    File "dist\Trade_Journal_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe"
    File "dist\trades.db" ; دیتابیس را هم کپی کن
    File "icon.ico" ; آیکون برنامه را هم کپی کن (برای میانبرها)
    File "version_info.py" ; فایل نسخه را هم کپی کن (برای نمایش نسخه)
    File "db_manager.py" ; ماژول دیتابیس را هم کپی کن (اگر فایل exe به آن اشاره می‌کند)

    ; ایجاد میانبر در دسکتاپ
    CreateShortcut "$DESKTOP\${APP_NAME}.lnk" "$INSTDIR\Trade_Journal_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe" "" "$INSTDIR\icon.ico" 0

    ; ایجاد میانبر در منوی استارت
    CreateDirectory "$SMPROGRAMS\${APP_NAME}"
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk" "$INSTDIR\Trade_Journal_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe" "" "$INSTDIR\icon.ico" 0
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk" "$INSTDIR\uninstall.exe"

    ; تنظیمات برای حذف برنامه در رجیستری
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayName" "${APP_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "UninstallString" "$\"$INSTDIR\uninstall.exe$\""
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "QuietUninstallString" "$\"$INSTDIR\uninstall.exe$\" /S"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "InstallLocation" "$INSTDIR"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "Publisher" "${COMPANY_NAME}"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "DisplayVersion" "${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}"
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}" "NoRepair" 1

    ; نوشتن فایل Uninstaller در پوشه نصب
    WriteUninstaller "$INSTDIR\uninstall.exe"

SectionEnd

; بخش نصب ویجت مستقل (اختیاری)
Section "ویجت تحلیل خطا (اختیاری)" SecWidget
    SectionIn RO ; Read-only (کاربر می‌تواند انتخاب کند)
    SetOutPath "$INSTDIR"

    ; کپی کردن فایل اجرایی ویجت
    ; حتماً نام فایل exe ویجت را با نام دقیق فعلی در پوشه dist جایگزین کن!
    ; (مثلا: Trade_Journal_Error_Widget_v1.00.00.exe)
    File "dist\Trade_Journal_Error_Widget_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe"

    ; ایجاد میانبر برای ویجت در منوی استارت
    CreateShortcut "$SMPROGRAMS\${APP_NAME}\${APP_NAME} Error Widget.lnk" "$INSTDIR\Trade_Journal_Error_Widget_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe" "" "$INSTDIR\icon.ico" 0
SectionEnd ; <-- این Section اینجا به پایان می‌رسد.

; بخش اجرای ویجت در هنگام راه‌اندازی ویندوز (Startup) - این یک Section کاملاً جداگانه است
Section "اجرای ویجت در هنگام راه‌اندازی ویندوز (Startup)" SecWidgetStartup
    SectionIn RO ; Read-only (کاربر می‌تواند انتخاب کند)
    
    ; این بخش باید تنها زمانی فعال باشد که SecWidget (ویجت اصلی) هم انتخاب شده باشد.
    ; این منطق به صورت خودکار توسط NSIS (چون هر دو RO هستند و کاربر می‌تواند انتخاب کند) مدیریت می‌شود
    ; اما برای اطمینان بیشتر، می‌توانید در تابع .onSelChange (یک تابع پیشرفته‌تر)
    ; این وابستگی را کدنویسی کنید. فعلاً برای سادگی، به همین شکل اکتفا می‌کنیم.

    ; این خط ویجت را به پوشه Startup کاربر اضافه می‌کند
    CreateShortcut "$STARTUP\${APP_NAME} Error Widget.lnk" "$INSTDIR\Trade_Journal_Error_Widget_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe" "" "$INSTDIR\icon.ico" 0
    ; یا می‌توانید از رجیستری استفاده کنید که مطمئن‌تر است:
    ; WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME} Error Widget" "$INSTDIR\Trade_Journal_Error_Widget_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe"
SectionEnd ; <-- این Section هم به پایان می‌رسد.


; --------------------------------------------------------------------------------------
; بخش حذف برنامه (Uninstaller)
; --------------------------------------------------------------------------------------
Section "Uninstall"
    ; حذف میانبرهای دسکتاپ
    Delete "$DESKTOP\${APP_NAME}.lnk"

    ; حذف میانبرهای منوی استارت
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME}.lnk"
    Delete "$SMPROGRAMS\${APP_NAME}\${APP_NAME} Error Widget.lnk" ; میانبر ویجت را هم حذف کن
    Delete "$SMPROGRAMS\${APP_NAME}\Uninstall.lnk"
    RMDir "$SMPROGRAMS\${APP_NAME}"

    ; حذف میانبر از Startup (اگر نصب شده باشد)
    Delete "$STARTUP\${APP_NAME} Error Widget.lnk"
    ; اگر از رجیستری استفاده کردی، این خط را اضافه کن:
    ; DeleteRegValue HKLM "Software\Microsoft\Windows\CurrentVersion\Run" "${APP_NAME} Error Widget"

    ; حذف فایل‌های نصب شده
    Delete "$INSTDIR\Trade_Journal_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe"
    Delete "$INSTDIR\Trade_Journal_Error_Widget_v${VERSION_MAJOR}.${VERSION_MINOR}.${VERSION_PATCH}.exe"
    Delete "$INSTDIR\trades.db"
    Delete "$INSTDIR\icon.ico"
    Delete "$INSTDIR\version_info.py"
    Delete "$INSTDIR\db_manager.py"
    Delete "$INSTDIR\uninstall.exe" ; فایل uninstaller را هم حذف کن

    ; حذف پوشه نصب (اگر خالی باشد)
    RMDir "$INSTDIR"

    ; حذف اطلاعات رجیستری Uninstaller
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\${APP_NAME}"
SectionEnd

; --------------------------------------------------------------------------------------
; توابع (Functions) - اگر نیاز بود
; --------------------------------------------------------------------------------------
; Function .onInit
;   ; کدهایی که قبل از شروع نصب اجرا می‌شوند
; FunctionEnd