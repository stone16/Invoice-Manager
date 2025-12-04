import { Resizable, ResizeCallbackData } from 'react-resizable';
import type { ComponentType } from 'react';

interface ResizableTitleProps {
  onResize: (e: React.SyntheticEvent, data: ResizeCallbackData) => void;
  width: number;
  [key: string]: unknown;
}

const ResizableTitle: ComponentType<ResizableTitleProps> = (props) => {
  const { onResize, width, ...restProps } = props;

  if (!width) {
    return <th {...restProps} />;
  }

  return (
    <Resizable
      width={width}
      height={0}
      handle={
        <span
          className="react-resizable-handle"
          onClick={(e) => e.stopPropagation()}
        />
      }
      onResize={onResize}
      draggableOpts={{ enableUserSelectHack: false }}
    >
      <th {...restProps} />
    </Resizable>
  );
};

export default ResizableTitle;
