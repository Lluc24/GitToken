import { toPng } from "html-to-image";
import { type RefObject, useState } from "react";
import { formatTokens } from "./format";

type ShareCardProps = {
  login: string;
  totalTokens: number;
  cardRef: RefObject<HTMLElement | null>;
};

const buttonClassName =
  "glass glass-interactive rounded-full px-4 py-2 font-medium text-sm text-white";

export function ShareCard({ login, totalTokens, cardRef }: ShareCardProps) {
  const [status, setStatus] = useState("");
  const profileUrl = `${window.location.origin}/${encodeURIComponent(login)}`;
  const badgeUrl = `${window.location.origin}/v1/badges/${encodeURIComponent(login)}.svg`;
  const postText = `${login} spent an estimated ${formatTokens(totalTokens)} tokens through coding agents. What's your GitToken card?`;
  const postUrl = `https://x.com/intent/post?${new URLSearchParams({ text: postText, url: profileUrl })}`;

  async function copy(text: string, copiedStatus: string) {
    await navigator.clipboard.writeText(text);
    setStatus(copiedStatus);
  }

  async function downloadPng() {
    if (cardRef.current) {
      const link = document.createElement("a");
      link.href = await toPng(cardRef.current, { pixelRatio: 2 });
      link.download = `${login}-gittoken.png`;
      link.click();
      setStatus("Card downloaded");
    }
  }

  return (
    <section
      aria-label="Share this card"
      className="flex flex-col items-center gap-2"
    >
      <div className="flex flex-wrap justify-center gap-2">
        <button type="button" onClick={downloadPng} className={buttonClassName}>
          Download
        </button>
        <button
          type="button"
          onClick={() => copy(profileUrl, "Link copied")}
          className={buttonClassName}
        >
          Copy link
        </button>
        <a
          href={postUrl}
          target="_blank"
          rel="noreferrer"
          className={buttonClassName}
        >
          Share on X
        </a>
        <button
          type="button"
          onClick={() =>
            copy(
              `[![${login}'s GitToken card](${badgeUrl})](${profileUrl})`,
              "README embed copied",
            )
          }
          className={buttonClassName}
        >
          Copy README embed
        </button>
      </div>
      <p role="status" className="min-h-5 text-muted text-sm">
        {status}
      </p>
    </section>
  );
}
