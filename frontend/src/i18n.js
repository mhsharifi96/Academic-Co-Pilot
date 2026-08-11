// Minimal two-language (en/fa) i18n, hand-rolled to keep the dependency-free
// posture of this app.  The chosen language drives three things: the strings
// below, the `lang` query param sent to the wizard API (which resolves
// per-language content columns server-side), and <html dir> — Persian is RTL.
//
// Only the wizard surface is translated; the older chat screens stay English.

import { createContext, createElement, useContext, useEffect, useMemo, useState } from "react";

const STORAGE_KEY = "paperagent.lang";

export const LANGS = ["en", "fa"];
export const DEFAULT_LANG = "en";

const STRINGS = {
  en: {
    "lang.name": "English",
    "lang.other": "فارسی",
    "lang.switchTo": "Switch to Persian",

    "nav.wizards": "Wizards",
    "nav.chat": "Chat",
    "nav.myRuns": "My workflows",
    "nav.backToApp": "Open the app",
    "nav.signIn": "Sign in",

    "landing.eyebrow": "Guided research workflows",
    "landing.title": "Get from a research goal to a finished draft.",
    "landing.subtitle":
      "Pick a workflow and your co-pilot walks you through it, one step at a time — screening literature, ingesting papers, planning, drafting with citations, and analysing your data.",
    "landing.cta": "Browse workflows",
    "landing.ctaSecondary": "Open the app",
    "landing.catalogTitle": "Choose a workflow",
    "landing.catalogSubtitle":
      "Each one is a short, ordered path. You can stop after any step and pick it up later.",
    "landing.empty": "No workflows have been published yet.",
    "landing.emptyHint": "An administrator can create one from the admin panel.",
    "landing.loading": "Loading workflows…",
    "landing.howTitle": "How it works",
    "landing.how1Title": "Pick a workflow",
    "landing.how1Body": "Every workflow is a sequence of focused steps with a clear goal.",
    "landing.how2Title": "Work through the steps",
    "landing.how2Body":
      "Each step gives the assistant its own brief. When the step's turns are used up, you move on automatically.",
    "landing.how3Title": "Continue any time",
    "landing.how3Body":
      "Your whole conversation is saved, so you can leave and come back where you stopped.",
    "landing.footer": "Academic Co-Pilot",

    "wizard.steps_one": "{n} step",
    "wizard.steps_other": "{n} steps",
    "wizard.start": "Start",
    "wizard.continue": "Continue",
    "wizard.startOrContinue": "Start or continue",
    "wizard.signInToStart": "Sign in to start",
    "wizard.pathTitle": "What you'll do",
    "wizard.back": "Back to workflows",
    "wizard.notFound": "That workflow doesn't exist or isn't published.",
    "wizard.noSteps": "This workflow has no steps yet.",
    "wizard.uncapped": "Open-ended",
    "wizard.capped_one": "{n} message",
    "wizard.capped_other": "{n} messages",

    "runner.stepOf": "Step {i} of {n}",
    "runner.messagesLeft_one": "{n} message left in this step",
    "runner.messagesLeft_other": "{n} messages left in this step",
    "runner.uncapped": "Open-ended step",
    "runner.placeholder": "Type your message…",
    "runner.send": "Send",
    "runner.thinking": "Co-Pilot is thinking…",
    "runner.advanced": "Step complete — moving to “{name}”.",
    "runner.completedTitle": "Workflow complete",
    "runner.completedBody": "You've finished every step. The full conversation is saved below.",
    "runner.abandoned": "This workflow was discarded.",
    "runner.startAgain": "Start it again",
    "runner.discard": "Discard workflow",
    "runner.discardConfirm":
      "Discard this workflow? The conversation is kept but you can't add to it.",
    "runner.finishStep": "Finish step",
    "runner.finishStepHint": "Move to the next step now, without using the messages left here.",
    "runner.finishWorkflow": "Finish workflow",
    "runner.finishWorkflowHint": "This is the last step — finishing completes the workflow.",
    "runner.nextIs": "Next: {name}",
    "runner.finishStepToHint": "Move on to “{name}” now, without using the messages left here.",
    "runner.suggestTitle": "This step looks done.",
    "runner.suggestBody": "Move on when you're ready, or keep working on it.",
    "runner.suggestStay": "Stay here",
    "runner.suggestGo": "Next step",
    "runner.welcome": "Send a message to begin.",
    "runner.loading": "Loading your workflow…",

    "runs.title": "My workflows",
    "runs.subtitle": "Pick up where you left off.",
    "runs.active": "In progress",
    "runs.finished": "Finished",
    "runs.empty": "You haven't started a workflow yet.",
    "runs.browse": "Browse workflows",
    "runs.open": "Open",
    "runs.updated": "Updated {when}",

    "admin.title": "Workflows",
    "admin.subtitle": "Create the guided paths users can follow.",
    "admin.new": "New workflow",
    "admin.edit": "Edit",
    "admin.delete": "Delete",
    "admin.deleteConfirm": "Delete this workflow? This cannot be undone.",
    "admin.published": "Published",
    "admin.draft": "Draft",
    "admin.publish": "Publish",
    "admin.unpublish": "Unpublish",
    "admin.empty": "No workflows yet.",
    "admin.internalName": "Internal name",
    "admin.internalNameHint": "Only admins see this. The slug is derived from it.",
    "admin.slug": "URL slug",
    "admin.slugHint": "Latin letters, digits and hyphens.",
    "admin.icon": "Icon",
    "admin.order": "Order",
    "admin.titleEn": "Title (English)",
    "admin.titleFa": "Title (Persian)",
    "admin.descEn": "Short description (English)",
    "admin.descFa": "Short description (Persian)",
    "admin.scopeGuardrail": "Apply the academic scope guardrail",
    "admin.scopeGuardrailHint":
      "Off lets this workflow accept messages outside the usual academic scope. Jailbreak protection always stays on.",
    "admin.steps": "Steps",
    "admin.addStep": "Add step",
    "admin.stepNameEn": "Step name (English)",
    "admin.stepNameFa": "Step name (Persian)",
    "admin.guideline": "Guideline prompt",
    "admin.guidelineHint":
      "Given to the assistant on every turn of this step. Users never see it.",
    "admin.maxMessages": "Max messages",
    "admin.maxMessagesHint":
      "Turns allowed before the workflow moves on. Leave blank for no limit.",
    "admin.moveUp": "Move up",
    "admin.moveDown": "Move down",
    "admin.noSteps": "No steps yet — add the first one.",
    "admin.stepDeleteConfirm": "Delete this step?",
    "admin.runCount_one": "{n} run",
    "admin.runCount_other": "{n} runs",

    "common.save": "Save",
    "common.saving": "Saving…",
    "common.cancel": "Cancel",
    "common.close": "Close",
    "common.back": "Back",
    "common.retry": "Try again",
    "common.required": "Required",
    "common.loading": "Loading…",
  },

  fa: {
    "lang.name": "فارسی",
    "lang.other": "English",
    "lang.switchTo": "تغییر به انگلیسی",

    "nav.wizards": "مسیرها",
    "nav.chat": "گفتگو",
    "nav.myRuns": "مسیرهای من",
    "nav.backToApp": "ورود به برنامه",
    "nav.signIn": "ورود",

    "landing.eyebrow": "مسیرهای پژوهشی گام‌به‌گام",
    "landing.title": "از هدف پژوهشی تا پیش‌نویس نهایی.",
    "landing.subtitle":
      "یک مسیر را انتخاب کنید تا دستیار شما گام‌به‌گام همراهی‌تان کند: غربالگری منابع، افزودن مقاله‌ها، برنامه‌ریزی، نگارش با ارجاع، و تحلیل داده‌ها.",
    "landing.cta": "دیدن مسیرها",
    "landing.ctaSecondary": "ورود به برنامه",
    "landing.catalogTitle": "یک مسیر انتخاب کنید",
    "landing.catalogSubtitle":
      "هر مسیر مجموعه‌ای کوتاه و ترتیب‌دار از گام‌هاست. هر جا خواستید متوقف شوید و بعداً ادامه دهید.",
    "landing.empty": "هنوز هیچ مسیری منتشر نشده است.",
    "landing.emptyHint": "مدیر می‌تواند از پنل مدیریت مسیر تازه‌ای بسازد.",
    "landing.loading": "در حال بارگذاری مسیرها…",
    "landing.howTitle": "چگونه کار می‌کند",
    "landing.how1Title": "یک مسیر انتخاب کنید",
    "landing.how1Body": "هر مسیر دنباله‌ای از گام‌های متمرکز با هدفی روشن است.",
    "landing.how2Title": "گام‌ها را پیش ببرید",
    "landing.how2Body":
      "هر گام دستور کار خودش را به دستیار می‌دهد. وقتی پیام‌های آن گام تمام شود، به‌طور خودکار به گام بعد می‌روید.",
    "landing.how3Title": "هر زمان ادامه دهید",
    "landing.how3Body":
      "تمام گفتگو ذخیره می‌شود؛ می‌توانید بیرون بروید و از همان‌جا ادامه دهید.",
    "landing.footer": "دستیار پژوهشی",

    "wizard.steps_one": "{n} گام",
    "wizard.steps_other": "{n} گام",
    "wizard.start": "شروع",
    "wizard.continue": "ادامه",
    "wizard.startOrContinue": "شروع یا ادامه",
    "wizard.signInToStart": "برای شروع وارد شوید",
    "wizard.pathTitle": "چه کاری انجام می‌دهید",
    "wizard.back": "بازگشت به مسیرها",
    "wizard.notFound": "این مسیر وجود ندارد یا منتشر نشده است.",
    "wizard.noSteps": "این مسیر هنوز گامی ندارد.",
    "wizard.uncapped": "بدون محدودیت",
    "wizard.capped_one": "{n} پیام",
    "wizard.capped_other": "{n} پیام",

    "runner.stepOf": "گام {i} از {n}",
    "runner.messagesLeft_one": "{n} پیام تا پایان این گام",
    "runner.messagesLeft_other": "{n} پیام تا پایان این گام",
    "runner.uncapped": "گام بدون محدودیت",
    "runner.placeholder": "پیام خود را بنویسید…",
    "runner.send": "ارسال",
    "runner.thinking": "دستیار در حال فکر کردن است…",
    "runner.advanced": "این گام تمام شد — رفتن به «{name}».",
    "runner.completedTitle": "مسیر کامل شد",
    "runner.completedBody": "همهٔ گام‌ها را به پایان رساندید. گفتگوی کامل در ادامه ذخیره شده است.",
    "runner.abandoned": "این مسیر کنار گذاشته شده است.",
    "runner.startAgain": "شروع دوباره",
    "runner.discard": "کنار گذاشتن مسیر",
    "runner.discardConfirm":
      "این مسیر کنار گذاشته شود؟ گفتگو می‌ماند اما نمی‌توانید چیزی به آن بیفزایید.",
    "runner.finishStep": "پایان این گام",
    "runner.finishStepHint": "همین حالا به گام بعد بروید، بدون مصرف پیام‌های باقی‌مانده.",
    "runner.finishWorkflow": "پایان مسیر",
    "runner.finishWorkflowHint": "این آخرین گام است — با پایان آن، مسیر کامل می‌شود.",
    "runner.nextIs": "بعدی: {name}",
    "runner.finishStepToHint": "همین حالا به «{name}» بروید، بدون مصرف پیام‌های باقی‌مانده.",
    "runner.suggestTitle": "به نظر می‌رسد این گام تمام شده است.",
    "runner.suggestBody": "هر وقت آماده بودید به گام بعد بروید، یا همین‌جا ادامه دهید.",
    "runner.suggestStay": "همین‌جا می‌مانم",
    "runner.suggestGo": "گام بعد",
    "runner.welcome": "برای شروع پیامی بفرستید.",
    "runner.loading": "در حال بارگذاری مسیر…",

    "runs.title": "مسیرهای من",
    "runs.subtitle": "از همان‌جا که رها کردید ادامه دهید.",
    "runs.active": "در جریان",
    "runs.finished": "پایان‌یافته",
    "runs.empty": "هنوز مسیری را شروع نکرده‌اید.",
    "runs.browse": "دیدن مسیرها",
    "runs.open": "بازکردن",
    "runs.updated": "به‌روزرسانی {when}",

    "admin.title": "مسیرها",
    "admin.subtitle": "مسیرهایی بسازید که کاربران دنبال می‌کنند.",
    "admin.new": "مسیر تازه",
    "admin.edit": "ویرایش",
    "admin.delete": "حذف",
    "admin.deleteConfirm": "این مسیر حذف شود؟ این کار بازگشت‌پذیر نیست.",
    "admin.published": "منتشرشده",
    "admin.draft": "پیش‌نویس",
    "admin.publish": "انتشار",
    "admin.unpublish": "لغو انتشار",
    "admin.empty": "هنوز مسیری ساخته نشده است.",
    "admin.internalName": "نام داخلی",
    "admin.internalNameHint": "فقط مدیران آن را می‌بینند. نشانی از روی آن ساخته می‌شود.",
    "admin.slug": "نشانی (slug)",
    "admin.slugHint": "حروف لاتین، رقم و خط تیره.",
    "admin.icon": "نماد",
    "admin.order": "ترتیب",
    "admin.titleEn": "عنوان (انگلیسی)",
    "admin.titleFa": "عنوان (فارسی)",
    "admin.descEn": "توضیح کوتاه (انگلیسی)",
    "admin.descFa": "توضیح کوتاه (فارسی)",
    "admin.scopeGuardrail": "اعمال محدودهٔ موضوعی دانشگاهی",
    "admin.scopeGuardrailHint":
      "خاموش کردن آن اجازه می‌دهد این مسیر پیام‌های خارج از محدودهٔ دانشگاهی را هم بپذیرد. محافظت در برابر دستکاری همیشه فعال است.",
    "admin.steps": "گام‌ها",
    "admin.addStep": "افزودن گام",
    "admin.stepNameEn": "نام گام (انگلیسی)",
    "admin.stepNameFa": "نام گام (فارسی)",
    "admin.guideline": "دستور گام",
    "admin.guidelineHint": "در هر نوبت این گام به دستیار داده می‌شود. کاربران آن را نمی‌بینند.",
    "admin.maxMessages": "بیشینهٔ پیام",
    "admin.maxMessagesHint":
      "تعداد نوبت‌های مجاز پیش از رفتن به گام بعد. برای نامحدود خالی بگذارید.",
    "admin.moveUp": "بالا بردن",
    "admin.moveDown": "پایین بردن",
    "admin.noSteps": "هنوز گامی نیست — اولین گام را بیفزایید.",
    "admin.stepDeleteConfirm": "این گام حذف شود؟",
    "admin.runCount_one": "{n} اجرا",
    "admin.runCount_other": "{n} اجرا",

    "common.save": "ذخیره",
    "common.saving": "در حال ذخیره…",
    "common.cancel": "انصراف",
    "common.close": "بستن",
    "common.back": "بازگشت",
    "common.retry": "تلاش دوباره",
    "common.required": "الزامی",
    "common.loading": "در حال بارگذاری…",
  },
};

export function isRtl(lang) {
  return lang === "fa";
}

function readStoredLang() {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (LANGS.includes(stored)) return stored;
  } catch {
    /* private mode / storage disabled */
  }
  return DEFAULT_LANG;
}

// Translate `key`, substituting {placeholders} from `vars`.  Keys ending in a
// count get a `_one` / `_other` suffix picked from `vars.n`.
export function translate(lang, key, vars) {
  const table = STRINGS[lang] || STRINGS[DEFAULT_LANG];
  let lookup = key;
  if (vars && typeof vars.n === "number") {
    const plural = `${key}_${vars.n === 1 ? "one" : "other"}`;
    if (plural in table || plural in STRINGS[DEFAULT_LANG]) lookup = plural;
  }
  let text = table[lookup] ?? STRINGS[DEFAULT_LANG][lookup] ?? key;
  if (vars) {
    for (const [name, value] of Object.entries(vars)) {
      text = text.split(`{${name}}`).join(String(value));
    }
  }
  return text;
}

const LangContext = createContext(null);

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(readStoredLang);

  // The document direction is global state that lives outside React, so it is
  // set here rather than in whichever component happens to render first.
  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = isRtl(lang) ? "rtl" : "ltr";
  }, [lang]);

  const value = useMemo(
    () => ({
      lang,
      rtl: isRtl(lang),
      setLang: (next) => {
        if (!LANGS.includes(next)) return;
        try {
          localStorage.setItem(STORAGE_KEY, next);
        } catch {
          /* ignore */
        }
        setLangState(next);
      },
      t: (key, vars) => translate(lang, key, vars),
    }),
    [lang]
  );

  return createElement(LangContext.Provider, { value }, children);
}

export function useT() {
  const ctx = useContext(LangContext);
  if (!ctx) {
    // Lets components render outside the provider (e.g. in isolation) without
    // crashing; they just get untranslated English.
    return {
      lang: DEFAULT_LANG,
      rtl: false,
      setLang: () => {},
      t: (key, vars) => translate(DEFAULT_LANG, key, vars),
    };
  }
  return ctx;
}
