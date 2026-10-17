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
    "landing.navLabel": "Page sections",
    "landing.navWhy": "Why us",
    "landing.navWorkflows": "Workflows",
    "landing.navPricing": "Pricing",
    "landing.whyTitle": "Why researchers use Academic Co-Pilot",
    "landing.whySubtitle":
      "One assistant for the whole paper — from the first search to the last citation — built around how academic work is actually done.",
    "landing.why1Title": "Citations you can trust",
    "landing.why1Body":
      "Drafts are grounded in the papers you ingest, not invented. References come out in IEEE, APA or Vancouver style.",
    "landing.why2Title": "Faster literature screening",
    "landing.why2Body":
      "Drop in a database export and get a colour-coded spreadsheet of relevant, maybe and excluded abstracts in minutes.",
    "landing.why3Title": "Your PDFs become a knowledge base",
    "landing.why3Body":
      "Upload papers once; the assistant searches them for every answer and every section it writes.",
    "landing.why4Title": "Data analysis built in",
    "landing.why4Body":
      "Ask questions about your CSV data and get statistics and publication-ready charts from a secure sandbox.",
    "landing.why5Title": "Guided, not overwhelming",
    "landing.why5Body":
      "Step-by-step workflows keep each stage focused, and your progress is saved so you can stop and resume any time.",
    "landing.why6Title": "English and Persian",
    "landing.why6Body":
      "The full interface works in both languages, with proper right-to-left layout for Persian.",
    "landing.chargeTitle": "Pay only for what you use",
    "landing.chargeSubtitle":
      "No subscription and no card required. Every new account starts with free credit; each message is billed by its actual usage, and you top up your wallet whenever you need more.",
    "landing.charge1Title": "Create a free account",
    "landing.charge1Body": "Sign up and receive starter credit to try the assistant right away.",
    "landing.charge2Title": "Open your wallet",
    "landing.charge2Body":
      "Click the balance chip at the top of the app and choose “Increase balance”.",
    "landing.charge3Title": "Choose amount and network",
    "landing.charge3Body":
      "Pick $5, $10, $20 or $30 and a crypto network: USDT (TRC-20, ERC-20, BEP-20, TON), BTC, ETH, TRX or TON.",
    "landing.charge4Title": "Pay and confirm",
    "landing.charge4Body":
      "We email you the wallet address. Send the payment, press “I've paid”, and your balance is credited once the transfer is confirmed.",
    "landing.chargeNote":
      "Send the exact amount on the network you chose only — payments sent on another network cannot be recovered.",
    "landing.chargeCta": "Create a free account",
    "landing.ctaTitle": "Start your next paper today",
    "landing.ctaBody": "Free starter credit. No subscription. Top up only when you need to.",
    "landing.metaTitle":
      "Academic Co-Pilot — AI research assistant for literature review & paper drafting",
    "landing.metaDescription":
      "AI research assistant that guides you from a research goal to a finished draft: screen literature, ingest PDFs, draft papers with real citations, and analyse your data. Pay as you go.",

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
    "suggest.trigger": "Suggest questions",
    "suggest.title": "You could ask",
    "suggest.loading": "Thinking of questions…",
    "suggest.refresh": "New ideas",
    "suggest.dismiss": "Hide suggestions",
    "suggest.send": "Send this question: {q}",
    "suggest.sendShort": "Send this question",
    "suggest.why": "Why:",
    "suggest.empty": "No suggestions right now — just type your question.",
    "runner.nextIs": "Next: {name}",
    "runner.finishStepToHint": "Move on to “{name}” now, without using the messages left here.",
    "runner.suggestTitle": "This step looks done.",
    "runner.suggestBody": "Move on when you're ready, or keep working on it.",
    "runner.suggestStay": "Stay here",
    "runner.suggestGo": "Next step",
    "runner.welcome": "Send a message to begin.",
    "runner.loading": "Loading your workflow…",
    "runner.attach": "Attach a file",
    "runner.attachHint": "Attach a PDF or CSV — the assistant can use it from your next message.",
    "runner.dropHere": "Drop your files here",
    "runner.uploading": "Uploading…",
    "runner.filesLabel": "Files in this workflow",
    "runner.balance": "Wallet",
    "runner.balanceHint": "Credit left in your wallet. Each message you send is billed to it.",

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
    "admin.addManySteps": "Add many…",
    "admin.bulkOutline": "Outline",
    "admin.bulkOutlineHint":
      "One step per line, in order. Numbering and bullets are ignored. Name a step in both languages with “English | فارسی”.",
    "admin.bulkPlaceholder":
      "Define the research question\nScreen the literature\nIngest the selected PDFs\nDraft the introduction",
    "admin.bulkCap": "Max messages per step",
    "admin.bulkCapHint":
      "Applied to every step created here. Leave blank for no limit — you can change each one afterwards.",
    "admin.bulkPromptNote":
      "Each step gets a placeholder guideline prompt naming it. Write the real prompt for each step below once they're created.",
    "admin.bulkCreate_one": "Create {n} step",
    "admin.bulkCreate_other": "Create {n} steps",
    "admin.bulkCreateEmpty": "Create steps",
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
    "ai.new": "Create with AI",
    "ai.title": "Create a workflow with AI",
    "ai.intro":
      "Describe what the workflow should help users do. The AI drafts the titles, description and every step with its guideline prompt. Nothing is saved until you review it.",
    "ai.goal": "What should this workflow do?",
    "ai.goalHint": "Write in English or Persian. Mention the result users should leave with.",
    "ai.goalPlaceholder":
      "e.g. Help a master's student turn a draft into a text backed by recent, reliable references: find the claims that need sources, search the last 3 years, verify every DOI, then add citations.",
    "ai.audience": "Who is it for? (optional)",
    "ai.audiencePlaceholder": "e.g. master's students in medical sciences",
    "ai.stepCount": "Number of steps",
    "ai.stepCountAuto": "Let the AI decide",
    "ai.maxMessages": "Max messages per step",
    "ai.generate": "Draft workflow",
    "ai.generating": "Drafting… this can take up to a minute",
    "ai.regenerate": "Draft again",
    "ai.review": "Review the draft",
    "ai.reviewHint": "Edit anything, remove steps you don't need, then create it. It is saved unpublished.",
    "ai.warnings": "Check before saving",
    "ai.removeStep": "Remove step",
    "ai.create": "Create workflow",
    "ai.creating": "Creating…",

    "common.save": "Save",
    "common.saving": "Saving…",
    "common.cancel": "Cancel",
    "common.close": "Close",
    "common.back": "Back",
    "common.retry": "Try again",
    "common.required": "Required",
    "common.loading": "Loading…",

    "topup.title": "Increase balance",
    "topup.chipHint": "Click to request more credit.",
    "topup.intro": "Choose an amount and the crypto network you'll pay on. We'll email you the wallet address to pay to.",
    "topup.email": "Email for payment details",
    "topup.amount": "Amount (USD)",
    "topup.network": "Payment network",
    "topup.cryptoNotice": "Payment is made in cryptocurrency. After you submit, an administrator emails you the wallet address for the network you chose. Send the payment, then come back here and press “I've paid”. Your balance is credited once the transfer is confirmed.",
    "topup.submit": "Request top-up",
    "topup.sending": "Sending…",
    "topup.errEmail": "Enter an email address.",
    "topup.wallet": "Pay to",
    "topup.txHash": "Transaction hash",
    "topup.txHashHint": "Optional — helps us find your payment",
    "topup.markPaid": "I've paid",
    "topup.cancelRequest": "Cancel request",
    "topup.history": "Previous requests",
    "topup.step.pending": "Requested",
    "topup.step.awaiting_payment": "Payment details sent",
    "topup.step.paid": "Paid",
    "topup.step.completed": "Credited",
    "topup.explain.pending": "Your request is in. An administrator will email you the wallet address for your network shortly.",
    "topup.explain.awaiting_payment": "We've emailed you the payment details (also shown below). Send the exact amount on the chosen network only, then press “I've paid”.",
    "topup.explain.paid": "Thanks! We're checking the transfer. Your balance is credited as soon as it's confirmed.",
    "topup.status.pending": "Requested",
    "topup.status.awaiting_payment": "Awaiting payment",
    "topup.status.paid": "Paid",
    "topup.status.completed": "Credited",
    "topup.status.rejected": "Rejected",
    "topup.status.cancelled": "Cancelled",
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
    "landing.navLabel": "بخش‌های صفحه",
    "landing.navWhy": "چرا ما",
    "landing.navWorkflows": "مسیرها",
    "landing.navPricing": "هزینه‌ها",
    "landing.whyTitle": "چرا پژوهشگران از دستیار پژوهشی استفاده می‌کنند",
    "landing.whySubtitle":
      "یک دستیار برای کل مقاله — از نخستین جستجو تا آخرین ارجاع — طراحی‌شده بر اساس روش واقعی کار پژوهشی.",
    "landing.why1Title": "ارجاع‌های قابل اعتماد",
    "landing.why1Body":
      "پیش‌نویس‌ها بر پایهٔ مقاله‌هایی است که خودتان افزوده‌اید، نه ساختگی. منابع با سبک IEEE، APA یا Vancouver ارائه می‌شوند.",
    "landing.why2Title": "غربالگری سریع‌تر منابع",
    "landing.why2Body":
      "خروجی پایگاه داده را بارگذاری کنید و در چند دقیقه صفحه‌گسترده‌ای رنگ‌بندی‌شده از چکیده‌های مرتبط، محتمل و حذف‌شده بگیرید.",
    "landing.why3Title": "PDFهای شما پایگاه دانش می‌شوند",
    "landing.why3Body":
      "مقاله‌ها را یک بار بارگذاری کنید؛ دستیار برای هر پاسخ و هر بخشی که می‌نویسد در آن‌ها جستجو می‌کند.",
    "landing.why4Title": "تحلیل داده درون برنامه",
    "landing.why4Body":
      "دربارهٔ داده‌های CSV خود بپرسید و آمار و نمودارهای آمادهٔ انتشار را از محیطی امن دریافت کنید.",
    "landing.why5Title": "گام‌به‌گام، بدون سردرگمی",
    "landing.why5Body":
      "مسیرهای گام‌به‌گام هر مرحله را متمرکز نگه می‌دارند و پیشرفت شما ذخیره می‌شود تا هر زمان ادامه دهید.",
    "landing.why6Title": "فارسی و انگلیسی",
    "landing.why6Body":
      "تمام رابط کاربری به هر دو زبان کار می‌کند و چیدمان راست‌به‌چپ فارسی به‌درستی پشتیبانی می‌شود.",
    "landing.chargeTitle": "فقط به اندازهٔ مصرف پرداخت کنید",
    "landing.chargeSubtitle":
      "بدون اشتراک و بدون نیاز به کارت بانکی. هر حساب تازه با اعتبار رایگان شروع می‌شود؛ هزینهٔ هر پیام بر اساس مصرف واقعی آن محاسبه می‌شود و هر زمان لازم بود کیف پول خود را شارژ می‌کنید.",
    "landing.charge1Title": "ساخت حساب رایگان",
    "landing.charge1Body": "ثبت‌نام کنید و اعتبار اولیه بگیرید تا همین حالا دستیار را امتحان کنید.",
    "landing.charge2Title": "باز کردن کیف پول",
    "landing.charge2Body":
      "روی نشان موجودی در بالای برنامه کلیک کنید و «افزایش موجودی» را انتخاب کنید.",
    "landing.charge3Title": "انتخاب مبلغ و شبکه",
    "landing.charge3Body":
      "۵، ۱۰، ۲۰ یا ۳۰ دلار و یک شبکهٔ رمزارز را انتخاب کنید: USDT (TRC-20، ERC-20، BEP-20، TON)، BTC، ETH، TRX یا TON.",
    "landing.charge4Title": "پرداخت و تأیید",
    "landing.charge4Body":
      "آدرس کیف پول را برایتان ایمیل می‌کنیم. پرداخت را انجام دهید، «پرداخت کردم» را بزنید و پس از تأیید تراکنش موجودی شما افزایش می‌یابد.",
    "landing.chargeNote":
      "مبلغ دقیق را فقط روی شبکهٔ انتخابی بفرستید — پرداخت روی شبکهٔ دیگر قابل بازگشت نیست.",
    "landing.chargeCta": "ساخت حساب رایگان",
    "landing.ctaTitle": "مقالهٔ بعدی‌تان را همین امروز شروع کنید",
    "landing.ctaBody": "اعتبار اولیهٔ رایگان. بدون اشتراک.",
    "landing.metaTitle": "دستیار پژوهشی — هوش مصنوعی برای مرور منابع و نگارش مقاله",
    "landing.metaDescription":
      "دستیار پژوهشی هوشمند که شما را از هدف پژوهشی تا پیش‌نویس نهایی همراهی می‌کند: غربالگری منابع، افزودن PDF، نگارش مقاله با ارجاع واقعی و تحلیل داده. پرداخت به اندازهٔ مصرف.",

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
    "suggest.trigger": "پیشنهاد پرسش",
    "suggest.title": "می‌توانید بپرسید",
    "suggest.loading": "در حال یافتن پرسش…",
    "suggest.refresh": "پیشنهاد تازه",
    "suggest.dismiss": "پنهان کردن پیشنهادها",
    "suggest.send": "ارسال این پرسش: {q}",
    "suggest.sendShort": "ارسال این پرسش",
    "suggest.why": "چرا:",
    "suggest.empty": "فعلاً پیشنهادی نیست — پرسش خود را بنویسید.",
    "runner.nextIs": "بعدی: {name}",
    "runner.finishStepToHint": "همین حالا به «{name}» بروید، بدون مصرف پیام‌های باقی‌مانده.",
    "runner.suggestTitle": "به نظر می‌رسد این گام تمام شده است.",
    "runner.suggestBody": "هر وقت آماده بودید به گام بعد بروید، یا همین‌جا ادامه دهید.",
    "runner.suggestStay": "همین‌جا می‌مانم",
    "runner.suggestGo": "گام بعد",
    "runner.welcome": "برای شروع پیامی بفرستید.",
    "runner.loading": "در حال بارگذاری مسیر…",
    "runner.attach": "پیوست فایل",
    "runner.attachHint": "یک فایل PDF یا CSV پیوست کنید — دستیار از پیام بعدی شما می‌تواند از آن استفاده کند.",
    "runner.dropHere": "فایل‌ها را این‌جا رها کنید",
    "runner.uploading": "در حال بارگذاری…",
    "runner.filesLabel": "فایل‌های این مسیر",
    "runner.balance": "کیف پول",
    "runner.balanceHint": "اعتبار باقی‌ماندهٔ کیف پول شما. هزینهٔ هر پیامی که می‌فرستید از آن کم می‌شود.",

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
    "admin.addManySteps": "افزودن گروهی…",
    "admin.bulkOutline": "فهرست گام‌ها",
    "admin.bulkOutlineHint":
      "در هر خط یک گام، به ترتیب. شماره و نشانهٔ فهرست نادیده گرفته می‌شود. برای نام دوزبانه از «English | فارسی» استفاده کنید.",
    "admin.bulkPlaceholder":
      "تعریف پرسش پژوهش\nغربالگری منابع\nبارگذاری مقاله‌های منتخب\nنگارش مقدمه",
    "admin.bulkCap": "بیشینهٔ پیام هر گام",
    "admin.bulkCapHint":
      "برای همهٔ گام‌هایی که این‌جا ساخته می‌شوند اعمال می‌شود. برای نامحدود خالی بگذارید؛ بعداً هر گام را جداگانه می‌توانید تغییر دهید.",
    "admin.bulkPromptNote":
      "برای هر گام یک دستور موقت با نام همان گام ساخته می‌شود. پس از ساخته شدن، دستور واقعی هر گام را در پایین بنویسید.",
    "admin.bulkCreate_one": "ساخت {n} گام",
    "admin.bulkCreate_other": "ساخت {n} گام",
    "admin.bulkCreateEmpty": "ساخت گام‌ها",
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
    "ai.new": "ساخت با هوش مصنوعی",
    "ai.title": "ساخت مسیر با هوش مصنوعی",
    "ai.intro":
      "بنویسید این مسیر باید به کاربران در چه کاری کمک کند. هوش مصنوعی عنوان‌ها، توضیح و همهٔ گام‌ها را همراه با دستورالعمل هر گام پیش‌نویس می‌کند. تا پیش از بازبینی شما چیزی ذخیره نمی‌شود.",
    "ai.goal": "این مسیر چه کاری انجام دهد؟",
    "ai.goalHint": "به فارسی یا انگلیسی بنویسید و بگویید کاربر در پایان چه چیزی به دست می‌آورد.",
    "ai.goalPlaceholder":
      "مثلاً: به دانشجوی کارشناسی ارشد کمک کن متن خود را با منابع جدید و معتبر غنی کند؛ ادعاهای نیازمند منبع را پیدا کند، پژوهش‌های سه سال اخیر را جست‌وجو کند، DOIها را راستی‌آزمایی کند و ارجاع‌ها را به متن اضافه کند.",
    "ai.audience": "مخاطب کیست؟ (اختیاری)",
    "ai.audiencePlaceholder": "مثلاً دانشجویان کارشناسی ارشد علوم پزشکی",
    "ai.stepCount": "تعداد گام‌ها",
    "ai.stepCountAuto": "به انتخاب هوش مصنوعی",
    "ai.maxMessages": "بیشینهٔ پیام هر گام",
    "ai.generate": "پیش‌نویس مسیر",
    "ai.generating": "در حال پیش‌نویس… ممکن است تا یک دقیقه طول بکشد",
    "ai.regenerate": "پیش‌نویس دوباره",
    "ai.review": "بازبینی پیش‌نویس",
    "ai.reviewHint": "هر بخشی را ویرایش کنید، گام‌های اضافه را حذف کنید و سپس بسازید. مسیر منتشرنشده ذخیره می‌شود.",
    "ai.warnings": "پیش از ذخیره بررسی کنید",
    "ai.removeStep": "حذف گام",
    "ai.create": "ساخت مسیر",
    "ai.creating": "در حال ساخت…",

    "common.save": "ذخیره",
    "common.saving": "در حال ذخیره…",
    "common.cancel": "انصراف",
    "common.close": "بستن",
    "common.back": "بازگشت",
    "common.retry": "تلاش دوباره",
    "common.required": "الزامی",
    "common.loading": "در حال بارگذاری…",

    "topup.title": "افزایش موجودی",
    "topup.chipHint": "برای درخواست اعتبار بیشتر کلیک کنید.",
    "topup.intro": "مبلغ و شبکهٔ رمزارزی که با آن پرداخت می‌کنید را انتخاب کنید. آدرس کیف پول مقصد را برایتان ایمیل می‌کنیم.",
    "topup.email": "ایمیل برای دریافت اطلاعات پرداخت",
    "topup.amount": "مبلغ (دلار)",
    "topup.network": "شبکهٔ پرداخت",
    "topup.cryptoNotice": "پرداخت با رمزارز انجام می‌شود. پس از ثبت درخواست، مدیر آدرس کیف پول شبکهٔ انتخابی را برایتان ایمیل می‌کند. پرداخت را انجام دهید، سپس به اینجا برگردید و «پرداخت کردم» را بزنید. پس از تأیید تراکنش، موجودی شما افزایش می‌یابد.",
    "topup.submit": "ثبت درخواست",
    "topup.sending": "در حال ارسال…",
    "topup.errEmail": "یک آدرس ایمیل وارد کنید.",
    "topup.wallet": "پرداخت به",
    "topup.txHash": "هش تراکنش",
    "topup.txHashHint": "اختیاری — به پیدا کردن پرداخت شما کمک می‌کند",
    "topup.markPaid": "پرداخت کردم",
    "topup.cancelRequest": "لغو درخواست",
    "topup.history": "درخواست‌های قبلی",
    "topup.step.pending": "ثبت شد",
    "topup.step.awaiting_payment": "اطلاعات پرداخت ارسال شد",
    "topup.step.paid": "پرداخت شد",
    "topup.step.completed": "به موجودی افزوده شد",
    "topup.explain.pending": "درخواست شما ثبت شد. مدیر به‌زودی آدرس کیف پول شبکهٔ شما را ایمیل می‌کند.",
    "topup.explain.awaiting_payment": "اطلاعات پرداخت را برایتان ایمیل کردیم (پایین هم آمده است). مبلغ دقیق را فقط روی شبکهٔ انتخابی بفرستید، سپس «پرداخت کردم» را بزنید.",
    "topup.explain.paid": "سپاس! در حال بررسی تراکنش هستیم. به‌محض تأیید، موجودی شما افزایش می‌یابد.",
    "topup.status.pending": "ثبت شد",
    "topup.status.awaiting_payment": "در انتظار پرداخت",
    "topup.status.paid": "پرداخت شد",
    "topup.status.completed": "افزوده شد",
    "topup.status.rejected": "رد شد",
    "topup.status.cancelled": "لغو شد",
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
