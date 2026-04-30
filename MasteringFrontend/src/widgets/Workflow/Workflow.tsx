const steps = ["Загрузка", "Разделение", "Живой микс", "Рендер", "Скачивание"];

type Props = {
  activeStage: number;
};

export function Workflow({activeStage}: Props) {
  return (
    <section className="workflow">
      {steps.map((item, index) => (
        <div className={index <= activeStage ? "step active" : "step"} key={item}>
          <span>{index + 1}</span>
          {item}
        </div>
      ))}
    </section>
  );
}
