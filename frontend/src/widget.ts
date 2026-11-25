import { compactNumberOptions } from "./format";
import type { GithubLogin } from "./login";
import { profilePath, userPath } from "./paths";

const profileRefreshMinutes = 6 * 60;
const errorRefreshMinutes = 15;

/** Post: a Scriptable (https://docs.scriptable.app) script that draws login's tokens and rarity from the /v1/users route. */
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

function refreshAfterMinutes(minutes) {
  widget.refreshAfterDate = new Date(Date.now() + minutes * 60 * 1000);
}

addText("GitToken", Font.semiboldSystemFont(12), 0.6);
widget.addSpacer();
try {
  const request = new Request(${JSON.stringify(`${origin}${userPath(login)}`)});
  const profile = await request.loadJSON();
  const statusCode = request.response.statusCode;
  if (statusCode === 200) {
    addText(new Intl.NumberFormat("en", ${JSON.stringify(compactNumberOptions)}).format(profile.total_tokens), Font.boldSystemFont(34), 1);
    addText(profile.rarity, Font.mediumSystemFont(14), 1);
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
addText(${JSON.stringify(`@${login}`)}, Font.systemFont(12), 0.6);

if (config.runsInWidget) {
  Script.setWidget(widget);
} else {
  await widget.presentSmall();
}
Script.complete();
`;
}
