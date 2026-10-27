import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { profileCardPath } from "./badges";
import { formatTokens } from "./format";
import { pressableClassName } from "./glass";
import { type Theme, useTheme } from "./theme";

type ShareCardProps = {
  login: string;
  totalTokens: number;
};

async function renderCardPng(login: string, theme: Theme): Promise<File> {
  const card = new Image();
  card.src = profileCardPath(login, theme);
  await card.decode();
  const canvas = document.createElement("canvas");
  canvas.width = card.naturalWidth * 2;
  canvas.height = card.naturalHeight * 2;
  canvas.getContext("2d")?.drawImage(card, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob | null>((resolve) =>
    canvas.toBlob(resolve, "image/png"),
  );
  if (blob === null) {
    throw new Error("The card could not be turned into an image");
  }
  return new File([blob], `${login}-gittoken.png`, { type: "image/png" });
}

export function ShareCard({ login, totalTokens }: ShareCardProps) {
  const [status, setStatus] = useState("");
  const theme = useTheme();
  const [cardFile, setCardFile] = useState<File | null>(null);
  const profileUrl = `${window.location.origin}/${encodeURIComponent(login)}`;
  const postText = `${login} spent an estimated ${formatTokens(totalTokens)} tokens through coding agents. What's your GitToken card?`;

  // Safari only opens the share sheet right after a click, so the image is ready before it.
  useEffect(() => {
    let isCurrent = true;
    renderCardPng(login, theme)
      .then((file) => {
        if (isCurrent) {
          setCardFile(file);
        }
      })
      .catch(() => {
        if (isCurrent) {
          setCardFile(null);
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [login, theme]);

  async function share() {
    if (typeof navigator.share === "function") {
      const shareData: ShareData = {
        title: "GitToken",
        text: postText,
        url: profileUrl,
      };
      try {
        await navigator.share(
          cardFile !== null && navigator.canShare({ files: [cardFile] })
            ? { ...shareData, files: [cardFile] }
            : shareData,
        );
      } catch (error) {
        // The user closing the share sheet is not a failure.
        if (!(error instanceof DOMException && error.name === "AbortError")) {
          setStatus("Sharing did not work this time");
        }
      }
    } else {
      try {
        await navigator.clipboard.writeText(profileUrl);
        setStatus("Link copied");
      } catch {
        setStatus(`Copy this link: ${profileUrl}`);
      }
    }
  }

  return (
    <section
      aria-label="Share this card"
      className="flex flex-col items-center gap-3"
    >
      <button
        type="button"
        onClick={share}
        className={`flex items-center gap-2 rounded-full bg-gradient-to-br from-cyan-300 via-violet-400 to-fuchsia-400 px-6 py-3 font-semibold text-night shadow-[inset_0_1px_0_rgb(255_255_255/0.7),0_8px_30px_-6px_rgb(167_139_250/0.8)] ${pressableClassName}`}
      >
        <svg
          viewBox="0 0 24 24"
          className="size-5"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
          aria-hidden="true"
        >
          <path d="M12 15V3m0 0L8 7m4-4 4 4" />
          <path d="M8 10H6a2 2 0 0 0-2 2v8a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-8a2 2 0 0 0-2-2h-2" />
        </svg>
        Share
      </button>
      <Link
        to={`/${encodeURIComponent(login)}/badges`}
        className="text-night/60 dark:text-white/60 text-sm hover:text-night dark:hover:text-white"
      >
        Add it to your README
      </Link>
      <p
        role="status"
        className="min-h-5 text-night/60 dark:text-white/60 text-sm"
      >
        {status}
      </p>
    </section>
  );
}
