const LAST_UPDATED = "4 November 2026";

interface Section {
  title: string;
  body?: string[];
  list?: string[];
  after?: string[];
}

const SECTIONS: Section[] = [
  {
    title: "About these terms",
    body: [
      "These terms cover your use of StudyMate, on the web and from your phone's Home Screen. By creating an account or using the app, you agree to them. If you don't agree, please don't use StudyMate.",
    ],
  },
  {
    title: "What StudyMate is",
    body: [
      "StudyMate helps you revise from your own course material: you add your courses and upload slides, PDFs, notes or photos of notes, and it makes flashcards, quizzes, exam-style papers and games from them, tracks what you know, and reminds you about lectures.",
      "StudyMate was built as a student project. It is not run by or connected to your university. Features may change, be unavailable at times, or be withdrawn.",
    ],
  },
  {
    title: "Your account",
    list: [
      "Give accurate details when you sign up, and keep your password to yourself.",
      "An account is for one person. You are responsible for what happens under it.",
      "If you are under 18, use StudyMate with the permission of a parent or guardian.",
    ],
  },
  {
    title: "AI-made questions are a study aid",
    body: [
      "Questions, answers, explanations, marking of written answers, and the text read from your files and photos are produced by AI from what you upload. They can be wrong, incomplete or worded differently from your lecturer. Check anything important against your lecture notes and course materials.",
      "Nothing in StudyMate is official exam material, and scores, mastery levels and the Coach's suggestions are estimates to guide your revision, not a prediction of your grades.",
    ],
  },
  {
    title: "Academic honesty",
    body: [
      "Use StudyMate for your own revision. Don't use it to complete assessed work or to cheat in tests or exams, and follow your university's rules on academic integrity.",
    ],
  },
  {
    title: "Your material",
    body: [
      "Files, notes and photos you upload stay yours, and other StudyMate users cannot see them. Upload only material you are allowed to use for study, such as your own notes and slides shared with your class, and don't upload other people's personal details.",
      "You allow StudyMate to store your material and to send it to the AI services it uses (Google Gemini and Mistral) to read it and write questions from it. StudyMate uses these services' free plans, under which a provider may use what it receives to improve its products, and its staff may read it. Don't upload anything sensitive or confidential. When you challenge a friend, they play the questions from that round, not your files.",
    ],
  },
  {
    title: "Friends and leaderboards",
    body: ["Leaderboards and challenges work when everyone is respectful. Don't:"],
    list: [
      "choose a username that is offensive or pretends to be someone else;",
      "harass, insult or threaten anyone, or send unwanted requests or challenges;",
      "share someone else's personal details;",
      "try to win by cheating the games or the scoring.",
    ],
    after: [
      "You can report or block anyone from the ... menu beside them. Reports are kept for review, and accounts that break these rules may be removed from leaderboards or disabled.",
    ],
  },
  {
    title: "Your information",
    list: [
      "StudyMate stores your email, name, username, school, programme, level and semester, your courses and uploads, your answers and scores, and your timetable.",
      "Friends see your name, username and XP. The board for your programme shows only your username (or first name and initial) and XP, and only if you join it under Settings, Privacy.",
      "Notifications are sent only after you allow them, and email reminders can be turned off under Settings, Lecture reminders.",
      "If the app crashes, an error report may be sent so it can be fixed. It does not include your email or what you uploaded.",
      "You can delete your account at any time under Settings, Delete account. This permanently removes your account and everything you added.",
    ],
  },
  {
    title: "Fair use",
    body: [
      "To keep the AI features working for everyone, each account has a daily limit on new question sets, uploads, photo reading and AI marking. The limits free up gradually over 24 hours.",
      "Don't try to get into other people's accounts or data, interfere with how the app runs, or copy its content in bulk.",
    ],
  },
  {
    title: "Changes and ending",
    body: [
      "StudyMate is provided as it is, without warranties. We are not responsible for lost files, results or other losses from using it, so keep your own copies of important material.",
      "These terms may change; the date at the top shows the latest version, and using the app after a change means you accept it. You can stop using StudyMate and delete your account whenever you like. Accounts that break these terms may be disabled.",
    ],
  },
];

/** Settings, Terms of use. */
export default function TermsOfUse() {
  return (
    <div className="card flex flex-col gap-5 p-5 text-sm leading-relaxed text-ink/75">
      <p className="text-xs text-ink/50">Last updated {LAST_UPDATED}</p>
      {SECTIONS.map((section) => (
        <section key={section.title} className="flex flex-col gap-2">
          <h3 className="text-base font-semibold text-ink">{section.title}</h3>
          {section.body?.map((text) => <p key={text}>{text}</p>)}
          {section.list && (
            <ul className="flex list-disc flex-col gap-1 pl-5">
              {section.list.map((text) => (
                <li key={text}>{text}</li>
              ))}
            </ul>
          )}
          {section.after?.map((text) => <p key={text}>{text}</p>)}
        </section>
      ))}
    </div>
  );
}
