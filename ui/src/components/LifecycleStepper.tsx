interface LifecycleStepperProps {
  status: string | null | undefined;
}

const steps = [
  { id: 'draft', label: 'work new' },
  { id: 'scope_proposed', label: 'scope' },
  { id: 'approval_requested', label: 'approval' },
  { id: 'approved', label: 'implement' },
  { id: 'validated', label: 'validate' },
  { id: 'delivered', label: 'deliver' },
  { id: 'closed', label: 'complete' }
];

const statusOrder: Record<string, number> = {
  draft: 0,
  scope_proposed: 1,
  approval_requested: 2,
  approved: 3,
  implemented: 4,
  validated: 5,
  delivered: 6,
  closed: 6
};

export function LifecycleStepper({ status }: LifecycleStepperProps) {
  const currentIndex = status ? (statusOrder[status] ?? -1) : -1;

  return (
    <ol className="lifecycle-stepper">
      {steps.map((step, index) => {
        const state = index < currentIndex ? 'complete' : index === currentIndex ? 'current' : 'upcoming';
        return (
          <li className={`lifecycle-step ${state}`} key={step.id}>
            <span>{index + 1}</span>
            <strong>{step.label}</strong>
          </li>
        );
      })}
    </ol>
  );
}
