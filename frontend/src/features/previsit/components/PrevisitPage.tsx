import { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { Check, Copy } from "lucide-react";
import { GlassCard, PageHeader } from "../../../components/apple";
import { postPrevisit } from "../../../lib/navigator-api";

const SPECIALTIES = [
  "Кардиолог",
  "Гастроэнтеролог",
  "ЛОР",
  "Терапевт / ВОП",
  "Эндокринолог",
  "Невролог / ортопед",
  "Дерматолог",
] as const;

export default function PrevisitPage() {
  const [specialty, setSpecialty] = useState<string>(SPECIALTIES[0]);
  const [doctor, setDoctor] = useState("");
  const [institution, setInstitution] = useState("");
  const [prompt, setPrompt] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [meta, setMeta] = useState<{
    complaints_used: number;
    labs_used: number;
    hint: string;
  } | null>(null);

  const gen = useMutation({
    mutationFn: () =>
      postPrevisit({
        specialty,
        doctor: doctor || undefined,
        institution: institution || undefined,
        include_abnormal_labs: true,
        include_open_complaints: true,
      }),
    onSuccess: (res) => {
      setPrompt(res.prompt);
      setMeta(res.meta);
      setCopied(false);
    },
  });

  const copy = async () => {
    if (!prompt) return;
    try {
      await navigator.clipboard.writeText(prompt);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = prompt;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
      setCopied(true);
    }
  };

  return (
    <div className="page-shell section-gap">
      <PageHeader subtitle="Zero-API MVP" title="Pre-Visit" />
      <p className="text-[13px] text-[#8E8E93] -mt-2">
        Собирает жалобы, анамнез и анализы → промпт для Gemini (без PDF)
      </p>

      <GlassCard padding="lg" className="space-y-3">
        <label className="block">
          <span className="text-[12px] font-semibold text-[#8E8E93] uppercase">
            Специалист
          </span>
          <select
            value={specialty}
            onChange={(e) => setSpecialty(e.target.value)}
            className="mt-1 w-full h-11 rounded-2xl bg-black/[0.04] px-3 text-[15px] outline-none"
          >
            {SPECIALTIES.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="text-[12px] font-semibold text-[#8E8E93] uppercase">
            Врач (опц.)
          </span>
          <input
            value={doctor}
            onChange={(e) => setDoctor(e.target.value)}
            placeholder="Спицарева О.Е."
            className="mt-1 w-full h-11 rounded-2xl bg-black/[0.04] px-3 text-[15px] outline-none"
          />
        </label>
        <label className="block">
          <span className="text-[12px] font-semibold text-[#8E8E93] uppercase">
            Учреждение (опц.)
          </span>
          <input
            value={institution}
            onChange={(e) => setInstitution(e.target.value)}
            placeholder="Новамед"
            className="mt-1 w-full h-11 rounded-2xl bg-black/[0.04] px-3 text-[15px] outline-none"
          />
        </label>
        <button
          type="button"
          onClick={() => gen.mutate()}
          disabled={gen.isPending}
          className="w-full h-11 rounded-2xl bg-[#5AC8FA] text-[#003A5A] font-semibold pressable disabled:opacity-50"
        >
          {gen.isPending ? "Собираю…" : "Собрать промпт"}
        </button>
      </GlassCard>

      {prompt && (
        <GlassCard padding="lg">
          {meta && (
            <p className="text-[12px] text-[#8E8E93] mb-3">
              жалоб: {meta.complaints_used} · анализов вне нормы: {meta.labs_used}
              <br />
              {meta.hint}
            </p>
          )}
          <pre className="text-[12px] leading-relaxed whitespace-pre-wrap break-words max-h-[45vh] overflow-y-auto bg-black/[0.03] rounded-2xl p-3">
            {prompt}
          </pre>
          <button
            type="button"
            onClick={copy}
            className="mt-3 w-full h-11 rounded-2xl bg-[#1C1C1E] text-white font-semibold flex items-center justify-center gap-2 pressable"
          >
            {copied ? (
              <>
                <Check className="w-4 h-4" /> Скопировано
              </>
            ) : (
              <>
                <Copy className="w-4 h-4" /> Скопировать промпт
              </>
            )}
          </button>
        </GlassCard>
      )}
    </div>
  );
}
