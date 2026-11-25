import type { GithubLogin } from "./login";
import { profilePath, userPath } from "./paths";

const profileRefreshMinutes = 6 * 60;
const errorRefreshMinutes = 15;

/** Post: a Scriptable (https://docs.scriptable.app) script that draws login's tokens, rarity and top agents from the /v1/users route. */
export function scriptableWidgetScript(
  origin: string,
  login: GithubLogin,
): string {
  return `/* GitToken widget for ${login}. Paste into a new Scriptable script, then add a Scriptable widget that runs it. */
const widget = new ListWidget();
widget.url = ${JSON.stringify(`${origin}${profilePath(login)}`)};
widget.backgroundColor = Color.dynamic(new Color("#ffffff"), new Color("#0b0b0f"));
const textColor = Color.dynamic(new Color("#0b0b0f"), Color.white());

function addText(text, font, opacity) {
  const line = widget.addText(text);
  line.font = font;
  line.textColor = textColor;
  line.textOpacity = opacity;
  line.minimumScaleFactor = 0.5;
  line.lineLimit = 1;
}

/* Matches _format_tokens in backend/src/gittoken/badge.py, so the widget reads like the badge. */
function formatTokens(tokens) {
  for (const [threshold, suffix] of [[1e9, "B"], [1e6, "M"], [1e3, "K"]]) {
    if (tokens >= threshold) {
      const tenths = Math.floor((tokens * 10 + threshold / 2) / threshold);
      const whole = Math.floor(tenths / 10);
      return (tenths % 10 === 0 ? String(whole) : whole + "." + (tenths % 10)) + suffix;
    }
  }
  return String(tokens);
}

function refreshAfterMinutes(minutes) {
  widget.refreshAfterDate = new Date(Date.now() + minutes * 60 * 1000);
}

try {
  const request = new Request(${JSON.stringify(`${origin}${userPath(login)}`)});
  const profile = await request.loadJSON();
  const statusCode = request.response.statusCode;
  if (statusCode === 200) {
    addText(formatTokens(profile.total_tokens), Font.boldSystemFont(30), 1);
    addText(profile.rarity, Font.mediumSystemFont(13), 0.8);
    widget.addSpacer();
    for (const agent of profile.top_agents) {
      addText(agent.name + " " + formatTokens(agent.tokens) + " · " + agent.percent + "%", Font.systemFont(11), 0.8);
    }
    refreshAfterMinutes(${profileRefreshMinutes});
  } else {
    addText(statusCode === 404 ? "No such GitHub user" : "Couldn't load tokens (HTTP " + statusCode + ")", Font.systemFont(12), 1);
    refreshAfterMinutes(${errorRefreshMinutes});
  }
} catch (error) {
  addText("Couldn't reach GitToken", Font.systemFont(12), 1);
  refreshAfterMinutes(${errorRefreshMinutes});
}
widget.addSpacer();
addText(${JSON.stringify(`@${login} · GitToken`)}, Font.systemFont(11), 0.6);

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentSmall();
}
Script.complete();
`;
}
