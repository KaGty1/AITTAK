import { Button } from "./Button.tsx";
import { Modal } from "./Modal.tsx";

export function ConfirmDialog({
  title,
  message,
  confirmLabel = "确认",
  danger = false,
  onConfirm,
  onClose,
}: {
  title: string;
  message: string;
  confirmLabel?: string;
  danger?: boolean;
  onConfirm: () => void;
  onClose: () => void;
}) {
  return (
    <Modal
      title={title}
      onClose={onClose}
      size="md"
      footer={
        <>
          <Button onClick={onClose}>取消</Button>
          <Button
            variant={danger ? "danger" : "primary"}
            onClick={() => {
              onConfirm();
              onClose();
            }}
          >
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="text-sm text-muted">{message}</p>
    </Modal>
  );
}
