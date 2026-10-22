import { useState } from "react";
import { Link } from "react-router-dom";
import { profileCardPath } from "./badges";
import { formatTokens } from "./format";
import { glassClassName, pressableClassName } from "./glass";

type ShareCardProps = {
  login: string;
  totalTokens: number;
};

const buttonClassName = `rounded-full px-4 py-2 font-medium text-sm text-white ${glassClassName} ${pressableClassName}`;

export function ShareCard({ login, totalTokens }: ShareCardProps) {
  const [status, setStatus] = useState("");
  const profileUrl = `${window.location.origin}/${encodeURIComponent(login)}`;
  const postText = `${login} spent an estimated ${formatTokens(totalTokens)} tokens through coding agents. What's your GitToken card?`;
  const postUrl = `https://x.com/intent/post?${new URLSearchParams({ text: postText, url: profileUrl })}`;

  async function copy(text: string, copiedStatus: string) {
    await navigator.clipboard.writeText(text);
    setStatus(copiedStatus);
  }

  async function downloadPng() {
    const card = new Image();
    card.src = profileCardPath(login);
    await card.decode();
    const canvas = document.createElement("canvas");
    canvas.width = card.naturalWidth * 2;
    canvas.height = card.naturalHeight * 2;
    const context = canvas.getContext("2d");
    if (context) {
      context.drawImage(card, 0, 0, canvas.width, canvas.height);
      const link = document.createElement("a");
      link.href = canvas.toDataURL("image/png");
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
        <Link
          to={`/${encodeURIComponent(login)}/badges`}
          className={buttonClassName}
        >
          README badges
        </Link>
      </div>
      <p role="status" className="min-h-5 text-muted text-sm">
        {status}
      </p>
    </section>
  );
}
