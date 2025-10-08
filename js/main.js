const AGENT_ID = 'agent_6301k71gqjvheebste5gnwxbz4v2';

const OPEN_IN_NEW_TAB = true;

const WIDGET_POSITION = 'bottom-right'; 

const img = document.querySelector('.image_to_show_1');

function injectElevenLabsWidget() {
  const ID = 'elevenlabs-convai-widget';

  const script = document.createElement('script');
  script.src = 'https://unpkg.com/@elevenlabs/convai-widget-embed';
  script.async = true;
  script.type = 'text/javascript';
  document.head.appendChild(script);

  const wrapper = document.createElement('div');
  wrapper.className = `convai-widget ${WIDGET_POSITION}`;

  const widget = document.createElement('elevenlabs-convai');
  widget.id = ID;
  widget.setAttribute('agent-id', AGENT_ID);
  widget.setAttribute('variant', 'full');

  const img = document.querySelector('.image_to_show_1');

  widget.addEventListener('elevenlabs-convai:call', (event) => {
    event.detail.config.clientTools = {
      ShowImage: ({ show }) => {
        console.log('show image.', show);
        if (show){
            img.style.display = 'block';
        }
        else{
            img.style.display = 'none';
        }

      },
    };
  });

  wrapper.appendChild(widget);
  document.body.appendChild(wrapper);
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', injectElevenLabsWidget);
} else {
  injectElevenLabsWidget();
}