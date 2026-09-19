import { ChevronDown } from "lucide-react";
import {
  Children,
  forwardRef,
  isValidElement,
  type KeyboardEvent,
  type ReactNode,
  type Ref,
  useCallback,
  useEffect,
  useId,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { createPortal } from "react-dom";
import { cn } from "@/shared/lib/cn";

export interface SelectChangeEvent {
  target: { value: string; name?: string };
}

export interface SelectProps {
  id?: string;
  name?: string;
  value?: string | number;
  defaultValue?: string | number;
  onChange?: (event: SelectChangeEvent) => void;
  onBlur?: () => void;
  disabled?: boolean;
  className?: string;
  children: ReactNode;
  "aria-label"?: string;
}

interface ParsedOption {
  value: string;
  label: string;
  disabled: boolean;
}

function flattenLabel(node: ReactNode): string {
  if (node === null || node === undefined || typeof node === "boolean") {
    return "";
  }
  if (typeof node === "string" || typeof node === "number") {
    return String(node);
  }
  if (Array.isArray(node)) {
    return node.map(flattenLabel).join("");
  }
  return "";
}

function parseOptions(children: ReactNode): ParsedOption[] {
  const options: ParsedOption[] = [];
  for (const child of Children.toArray(children)) {
    if (!isValidElement(child) || child.type !== "option") {
      continue;
    }
    const props = child.props as {
      value?: string | number;
      disabled?: boolean;
      children?: ReactNode;
    };
    options.push({
      value: String(props.value ?? ""),
      label: flattenLabel(props.children),
      disabled: Boolean(props.disabled),
    });
  }
  return options;
}

function setRef<T>(ref: Ref<T> | undefined, node: T | null): void {
  if (typeof ref === "function") {
    ref(node);
  } else if (ref) {
    (ref as { current: T | null }).current = node;
  }
}

interface PanelCoords {
  top: number;
  left: number;
  width: number;
  maxHeight: number;
}

const MARGIN = 6;

export const Select = forwardRef<HTMLButtonElement, SelectProps>(function Select(
  { id, name, value, defaultValue, onChange, onBlur, disabled, className, children, ...rest },
  ref,
) {
  const options = useMemo(() => parseOptions(children), [children]);
  const [uncontrolled, setUncontrolled] = useState<string | undefined>(
    defaultValue === undefined ? undefined : String(defaultValue),
  );
  const current = value !== undefined ? String(value) : (uncontrolled ?? "");
  const selectedIndex = options.findIndex((option) => option.value === current);
  const selected = selectedIndex >= 0 ? options[selectedIndex] : undefined;

  const [open, setOpen] = useState(false);
  const [activeIndex, setActiveIndex] = useState(0);
  const [coords, setCoords] = useState<PanelCoords | null>(null);
  const triggerRef = useRef<HTMLButtonElement | null>(null);
  const panelRef = useRef<HTMLDivElement | null>(null);
  const listboxId = useId();
  const optionDomId = (index: number) => `${listboxId}-opt-${index}`;

  const close = useCallback(
    (blur = false) => {
      setOpen(false);
      if (blur) {
        onBlur?.();
      }
    },
    [onBlur],
  );

  const commit = useCallback(
    (option: ParsedOption) => {
      if (option.disabled) {
        return;
      }
      if (value === undefined) {
        setUncontrolled(option.value);
      }
      onChange?.({ target: { value: option.value, name } });
      setOpen(false);
      onBlur?.();
      triggerRef.current?.focus();
    },
    [name, onBlur, onChange, value],
  );

  const openPanel = useCallback(() => {
    if (disabled) {
      return;
    }
    setActiveIndex(selectedIndex >= 0 ? selectedIndex : 0);
    setCoords(null);
    setOpen(true);
  }, [disabled, selectedIndex]);

  useLayoutEffect(() => {
    if (!open) {
      return;
    }
    const trigger = triggerRef.current;
    const panel = panelRef.current;
    if (!trigger || !panel) {
      return;
    }
    const rect = trigger.getBoundingClientRect();
    const panelHeight = panel.offsetHeight;
    const spaceBelow = window.innerHeight - rect.bottom - MARGIN;
    const spaceAbove = rect.top - MARGIN;
    // prefere abrir para baixo; só inverte se não houver espaço minimo abaixo
    const minBelow = 200;
    const above = spaceBelow < minBelow && spaceAbove > spaceBelow;
    const maxHeight = Math.min(340, Math.max(140, above ? spaceAbove : spaceBelow));
    const height = Math.min(panelHeight, maxHeight);
    setCoords({
      left: Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8)),
      width: rect.width,
      top: above ? rect.top - height - MARGIN : rect.bottom + MARGIN,
      maxHeight,
    });
  }, [open]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const onPointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      if (triggerRef.current?.contains(target) || panelRef.current?.contains(target)) {
        return;
      }
      close();
    };
    const onDismiss = () => {
      close();
    };
    document.addEventListener("mousedown", onPointerDown);
    document.addEventListener("scroll", onDismiss, true);
    window.addEventListener("resize", onDismiss);
    return () => {
      document.removeEventListener("mousedown", onPointerDown);
      document.removeEventListener("scroll", onDismiss, true);
      window.removeEventListener("resize", onDismiss);
    };
  }, [open, close]);

  useEffect(() => {
    if (!open) {
      return;
    }
    const option = panelRef.current?.querySelectorAll('[role="option"]')[activeIndex];
    option?.scrollIntoView({ block: "nearest" });
  }, [open, activeIndex]);

  const onKeyDown = (event: KeyboardEvent<HTMLButtonElement>) => {
    if (disabled) {
      return;
    }
    if (!open) {
      if (
        event.key === "ArrowDown" ||
        event.key === "ArrowUp" ||
        event.key === "Enter" ||
        event.key === " "
      ) {
        event.preventDefault();
        openPanel();
      }
      return;
    }
    switch (event.key) {
      case "ArrowDown":
        event.preventDefault();
        setActiveIndex((index) => Math.min(index + 1, options.length - 1));
        break;
      case "ArrowUp":
        event.preventDefault();
        setActiveIndex((index) => Math.max(index - 1, 0));
        break;
      case "Home":
        event.preventDefault();
        setActiveIndex(0);
        break;
      case "End":
        event.preventDefault();
        setActiveIndex(options.length - 1);
        break;
      case "Enter":
      case " ": {
        event.preventDefault();
        const option = options[activeIndex];
        if (option) {
          commit(option);
        }
        break;
      }
      case "Escape":
        event.preventDefault();
        event.stopPropagation();
        close(true);
        break;
      case "Tab":
        close(true);
        break;
    }
  };

  return (
    <>
      <button
        {...rest}
        ref={(node) => {
          triggerRef.current = node;
          setRef(ref, node);
        }}
        type="button"
        id={id}
        role="combobox"
        aria-haspopup="listbox"
        aria-expanded={open}
        aria-controls={open ? listboxId : undefined}
        aria-activedescendant={open ? optionDomId(activeIndex) : undefined}
        disabled={disabled}
        className={cn("input sel-trigger", className)}
        onClick={() => {
          if (open) {
            close(true);
          } else {
            openPanel();
          }
        }}
        onKeyDown={onKeyDown}
      >
        <span className="truncate">{selected?.label ?? ""}</span>
        <ChevronDown size={14} strokeWidth={2} aria-hidden className="sel-caret" />
      </button>
      {open
        ? createPortal(
            <div
              ref={panelRef}
              id={listboxId}
              role="listbox"
              aria-label={rest["aria-label"]}
              className="sel-panel"
              style={
                coords
                  ? {
                      top: coords.top,
                      left: coords.left,
                      width: coords.width,
                      maxHeight: coords.maxHeight,
                    }
                  : {
                      top: -9999,
                      left: -9999,
                      width: triggerRef.current?.offsetWidth,
                      visibility: "hidden",
                    }
              }
            >
              {options.map((option, index) => (
                <div
                  key={option.value}
                  id={optionDomId(index)}
                  role="option"
                  tabIndex={-1}
                  aria-selected={option.value === current}
                  aria-disabled={option.disabled || undefined}
                  data-active={index === activeIndex || undefined}
                  className="sel-option"
                  onMouseDown={(event) => {
                    event.preventDefault();
                  }}
                  onMouseEnter={() => {
                    setActiveIndex(index);
                  }}
                  onClick={() => {
                    commit(option);
                  }}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      commit(option);
                    }
                  }}
                >
                  <span className="truncate">{option.label}</span>
                </div>
              ))}
            </div>,
            document.body,
          )
        : null}
    </>
  );
});
