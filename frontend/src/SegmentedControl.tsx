import type { ReactNode } from "react";

type SegmentedControlVariant = "icon" | "text";

const classNamesByVariant: Record<
  SegmentedControlVariant,
  { control: string; option: string; unselectedOption: string }
> = {
  icon: {
    control: "p-0.5",
    option: "flex size-9 items-center justify-center sm:size-8",
    unselectedOption: "text-night/60 dark:text-white/60",
  },
  text: {
    control: "p-1",
    option: "px-3 py-2 sm:py-1",
    unselectedOption: "text-night/70 dark:text-white/70",
  },
};

type SegmentedControlProps<Option extends string> = {
  label: string;
  variant: SegmentedControlVariant;
  options: readonly Option[];
  selected: Option;
  onSelect: (option: Option) => void;
  renderOption: (option: Option) => ReactNode;
};

export function SegmentedControl<Option extends string>({
  label,
  variant,
  options,
  selected,
  onSelect,
  renderOption,
}: SegmentedControlProps<Option>) {
  const classNames = classNamesByVariant[variant];
  return (
    <fieldset
      className={`flex w-fit rounded-full bg-night/10 dark:bg-white/10 text-sm ${classNames.control}`}
    >
      <legend className="sr-only">{label}</legend>
      {options.map((option) => (
        <button
          key={option}
          type="button"
          aria-pressed={option === selected}
          onClick={() => onSelect(option)}
          className={`rounded-full transition-colors ${classNames.option} ${option === selected ? "bg-night dark:bg-white font-medium text-white dark:text-night" : `${classNames.unselectedOption} hover:text-night dark:hover:text-white`}`}
        >
          {renderOption(option)}
        </button>
      ))}
    </fieldset>
  );
}
