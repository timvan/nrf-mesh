/* TODO */
/* 
CHECK HOW LEDS AFFECT THE PINS - should we remove the hal and leds


 */
/***************/

#include <stdint.h>
#include <string.h>

/* HAL */
#include "boards.h"
// #include "simple_hal.h"
#include "app_timer.h"

/* Core */
#include "nrf_mesh_config_core.h"
#include "nrf_mesh_gatt.h"
#include "nrf_mesh_configure.h"
#include "nrf_mesh.h"
#include "mesh_stack.h"
#include "device_state_manager.h"
#include "access_config.h"
#include "proxy.h"

/* Provisioning and configuration */
#include "mesh_provisionee.h"
#include "mesh_app_utils.h"

/* Models */
#include "generic_onoff_server.h"
#include "generic_onoff_client.h"
#include "simple_on_off_server.h"

/* Logging and RTT */
#include "log.h"
#include "rtt_input.h"

/* Example specific includes */
#include "app_config.h"
#include "example_common.h"
#include "nrf_mesh_config_examples.h"
#include "light_switch_example_common.h"
#include "app_onoff.h"
#include "ble_softdevice_support.h"

#include "nrfx_gpiote.h"

#define APP_ONOFF_ELEMENT_INDEX     (1)

#define APP_STATE_OFF                (0)
#define APP_STATE_ON                 (1)
#define APP_UNACK_MSG_REPEAT_COUNT   (2)

#define PIN_NUMBER 23
#define P_INPUT true
#define P_OUTPUT false
#define P_STARTING_STATE P_OUTPUT

static bool m_device_provisioned;

APP_TIMER_DEF(m_onoff_server_0_timer);
static app_onoff_server_t m_onoff_server_0;

static generic_onoff_client_t m_client;

static simple_on_off_server_t m_simple_on_off_server;

static bool pin_state;
static int pin_number;

// fwd declerartions
static void node_reset(void);

/*************************************************************************************************/
/**** START  ****/

static void provisioning_aborted_cb(void)
{
    // hal_led_blink_stop(); // TODO DELETE HAL
}


static void device_identification_start_cb(uint8_t attention_duration_s)
{
    // TODO DELETE HAL
    // hal_led_mask_set(LEDS_MASK, false);
    // hal_led_blink_ms(BSP_LED_2_MASK  | BSP_LED_3_MASK,
    //                  LED_BLINK_ATTENTION_INTERVAL_MS,
    //                  LED_BLINK_ATTENTION_COUNT(attention_duration_s));
}

static void provisioning_complete_cb(void)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Successfully provisioned\n");

#if MESH_FEATURE_GATT_ENABLED
    /* Restores the application parameters after switching from the Provisioning
     * service to the Proxy  */
    gap_params_init();
    conn_params_init();
#endif

    dsm_local_unicast_address_t node_address;
    dsm_local_unicast_addresses_get(&node_address);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Node Address: 0x%04x \n", node_address.address_start);

    // TODO DELETE HAL
    // hal_led_blink_stop();
    // hal_led_mask_set(LEDS_MASK, LED_MASK_STATE_OFF);
    // hal_led_blink_ms(LEDS_MASK, LED_BLINK_INTERVAL_MS, LED_BLINK_CNT_PROV);
}

static bool app_simple_onoff_server_set_cb(const simple_on_off_server_t * p_self, bool on); // TODO SORT THIS FORWARD DECLERATION
static void rtt_input_handler(int key)
{
    key = key - '0';
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "rtt %u pressed\n", key);

    uint32_t status = NRF_SUCCESS;
    generic_onoff_set_params_t set_params;
    model_transition_t transition_params;
    static uint8_t tid = 0;
    bool new_state;

    /* Button 1: On, Button 2: Off, Client[0]
     * Button 2: On, Button 3: Off, Client[1]
     */

    switch(key)
    {
        case 0:
        case 2:
            set_params.on_off = APP_STATE_ON;
            break;

        case 1:
        case 3:
            set_params.on_off = APP_STATE_OFF;
            break;
            
    }

    set_params.tid = tid++;
    transition_params.delay_ms = APP_CONFIG_ONOFF_DELAY_MS;
    transition_params.transition_time_ms = APP_CONFIG_ONOFF_TRANSITION_TIME_MS;

    switch (key)
    {
        case 0:
        case 1:
            /* Demonstrate acknowledged transaction, using 1st client model instance */
            /* In this examples, users will not be blocked if the model is busy */
            (void)access_model_reliable_cancel(m_client.model_handle);
            status = generic_onoff_client_set(&m_client, &set_params, &transition_params);
            // hal_led_pin_set(BSP_LED_0, set_params.on_off); // TODO DELETE HAL
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Sending msg: ONOFF SET ACK %d\n", set_params.on_off);
            break;

        case 2:
        case 3:
            /* Demonstrate un-acknowledged transaction, using 2nd client model instance */
            status = generic_onoff_client_set_unack(&m_client, &set_params,
                                                    &transition_params, APP_UNACK_MSG_REPEAT_COUNT);
            // hal_led_pin_set(BSP_LED_1, set_params.on_off); // TODO DELETE HAL
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Sending msg: ONOFF SET %d\n", set_params.on_off);
            break;
        case 4:
            status = generic_onoff_client_get(&m_client);
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Sending msg: ONOFF GET \n");
            break;
        case 5:
            new_state = P_INPUT;
            if(pin_state == P_INPUT){
              new_state = P_OUTPUT;
            }
            app_simple_onoff_server_set_cb(&m_simple_on_off_server, new_state);
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "swapping gpio state \n");
            break;
        case 6:
            node_reset();
            break;

    }

    switch (status)
    {
        case NRF_SUCCESS:
            break;

        case NRF_ERROR_NO_MEM:
        case NRF_ERROR_BUSY:
        case NRF_ERROR_INVALID_STATE:
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client cannot send\n");
            // hal_led_blink_ms(LEDS_MASK, LED_BLINK_SHORT_INTERVAL_MS, LED_BLINK_CNT_NO_REPLY); // TODO DELETE HAL
            break;

        case NRF_ERROR_INVALID_PARAM:
            /* Publication not enabled for this client. One (or more) of the following is wrong:
             * - An application key is missing, or there is no application key bound to the model
             * - The client does not have its publication state set
             *
             * It is the provisioner that adds an application key, binds it to the model and sets
             * the model's publication state.
             */
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Publication not configured for client\n");
            break;

        default:
            ERROR_CHECK(status);
            break;
    }
}

static void start(void)
{
    rtt_input_enable(rtt_input_handler, RTT_INPUT_POLL_PERIOD_MS);

    if (!m_device_provisioned)
    {
        static const uint8_t static_auth_data[NRF_MESH_KEY_SIZE] = STATIC_AUTH_DATA;
        mesh_provisionee_start_params_t prov_start_params =
        {
            .p_static_data    = static_auth_data,
            .prov_complete_cb = provisioning_complete_cb,
            .prov_device_identification_start_cb = device_identification_start_cb,
            .prov_device_identification_stop_cb = NULL,
            .prov_abort_cb = provisioning_aborted_cb,
            .p_device_uri = EX_URI_LS_SERVER
        };
        ERROR_CHECK(mesh_provisionee_prov_start(&prov_start_params));
    }

    mesh_app_uuid_print(nrf_mesh_configure_device_uuid_get());

    ERROR_CHECK(mesh_stack_start());

    // hal_led_mask_set(LEDS_MASK, LED_MASK_STATE_OFF); // TODO DELETE HAL
    // hal_led_blink_ms(LEDS_MASK, LED_BLINK_INTERVAL_MS, LED_BLINK_CNT_START); // TODO DELETE HAL
}

/*************************************************************************************************/
/**** INIT  ****/

/**** SERVER CBS ****/
static void app_onoff_server_set_cb(const app_onoff_server_t * p_server, bool onoff)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Server - Setting GPIO value: %d\n", onoff)
    if(onoff){
        nrfx_gpiote_out_set(pin_number);
    } else {
        nrfx_gpiote_out_clear(pin_number);
    }
}

static void app_onoff_server_get_cb(const app_onoff_server_t * p_server, bool * p_present_onoff)
{
    *p_present_onoff = nrf_gpio_pin_read(pin_number);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Server - getting GPIO value: %d\n", p_present_onoff)
}

/**** CLIENT CBS ****/
static void app_gen_onoff_client_publish_interval_cb(access_model_handle_t handle, void * p_self);
static void app_generic_onoff_client_status_cb(const generic_onoff_client_t * p_self,
                                               const access_message_rx_meta_t * p_meta,
                                               const generic_onoff_status_params_t * p_in);
static void app_gen_onoff_client_transaction_status_cb(access_model_handle_t model_handle,
                                                       void * p_args,
                                                       access_reliable_status_t status);

const generic_onoff_client_callbacks_t client_cbs =
{
    .onoff_status_cb = app_generic_onoff_client_status_cb,
    .ack_transaction_status_cb = app_gen_onoff_client_transaction_status_cb,
    .periodic_publish_cb = app_gen_onoff_client_publish_interval_cb
};

/* This callback is called periodically if model is configured for periodic publishing */
static void app_gen_onoff_client_publish_interval_cb(access_model_handle_t handle, void * p_self)
{
     __LOG(LOG_SRC_APP, LOG_LEVEL_WARN, "Client - publish interval cb.\n");
}

/* Acknowledged transaction status callback, if acknowledged transfer fails, application can
* determine suitable course of action (e.g. re-initiate previous transaction) by using this
* callback.
*/
static void app_gen_onoff_client_transaction_status_cb(access_model_handle_t model_handle,
                                                       void * p_args,
                                                       access_reliable_status_t status)
{
    switch(status)
    {
        case ACCESS_RELIABLE_TRANSFER_SUCCESS:
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client - Acknowledged transfer success.\n");
            break;

        case ACCESS_RELIABLE_TRANSFER_TIMEOUT:
            // hal_led_blink_ms(LEDS_MASK, LED_BLINK_SHORT_INTERVAL_MS, LED_BLINK_CNT_NO_REPLY); // TODO DELETE HAL
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client - Acknowledged transfer timeout.\n");
            break;

        case ACCESS_RELIABLE_TRANSFER_CANCELLED:
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client - Acknowledged transfer cancelled.\n");
            break;

        default:
            ERROR_CHECK(NRF_ERROR_INTERNAL);
            break;
    }
}

/* Generic OnOff client model interface: Process the received status message in this callback */
static void app_generic_onoff_client_status_cb(const generic_onoff_client_t * p_self,
                                               const access_message_rx_meta_t * p_meta,
                                               const generic_onoff_status_params_t * p_in)
{
    if (p_in->remaining_time_ms > 0)
    {
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client - OnOff server: 0x%04x, Present OnOff: %d, Target OnOff: %d, Remaining Time: %d ms\n",
              p_meta->src.value, p_in->present_on_off, p_in->target_on_off, p_in->remaining_time_ms);
    }
    else
    {
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client - OnOff server: 0x%04x, Present OnOff: %d\n",
              p_meta->src.value, p_in->present_on_off);
    }
}

/**** SIMPLE SERVER CBS - FOR CHANGING PIN STATE ****/

// forward declerations
static void gpio_init_input();
static void gpio_init_output();

static bool app_simple_onoff_server_get_cb(const simple_on_off_server_t * p_self)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Simple server-on-off - get\n");
    return pin_state;
}

static bool app_simple_onoff_server_set_cb(const simple_on_off_server_t * p_self, bool on)
{
    if(on){
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Simple server-on-off - set as P_INPUT \n");
    } else {
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Simple server-on-off - set as P_OUTPUT \n");
    }
    
    if(pin_state != on){
        if(on == P_INPUT){
            gpio_init_input();
        } else {
            gpio_init_output();
        }
    }
    
    pin_state = on;
    return pin_state;
}

/*** INIT CBS ****/

static void models_init_cb(void)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Initializing and adding models\n");

    /* init server */

    m_onoff_server_0.server.settings.force_segmented = APP_CONFIG_FORCE_SEGMENTATION;
    m_onoff_server_0.server.settings.transmic_size = APP_CONFIG_MIC_SIZE;
    m_onoff_server_0.p_timer_id = &m_onoff_server_0_timer;
    m_onoff_server_0.onoff_set_cb = app_onoff_server_set_cb;
    m_onoff_server_0.onoff_get_cb = app_onoff_server_get_cb;

    ERROR_CHECK(app_onoff_init(&m_onoff_server_0, APP_ONOFF_ELEMENT_INDEX));


    /* init client */

    m_client.settings.p_callbacks = &client_cbs;
    m_client.settings.timeout = 0;
    m_client.settings.force_segmented = APP_CONFIG_FORCE_SEGMENTATION;
    m_client.settings.transmic_size = APP_CONFIG_MIC_SIZE;
    ERROR_CHECK(generic_onoff_client_init(&m_client, APP_ONOFF_ELEMENT_INDEX));
    

    /* init config server */

    m_simple_on_off_server.get_cb = &app_simple_onoff_server_get_cb;
    m_simple_on_off_server.set_cb = &app_simple_onoff_server_set_cb;
    ERROR_CHECK(simple_on_off_server_init(&m_simple_on_off_server, APP_ONOFF_ELEMENT_INDEX));
}

/*************************************************************************************************/

/* TVE STUFF FOR GPIO PINS */

static void in_pin_handler(nrfx_gpiote_pin_t pin, nrf_gpiote_polarity_t action)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Sending ONOFF set %d", pin_state);
    
    generic_onoff_set_params_t p_params;
    model_transition_t transition_params;
    static uint8_t tid = 0;
    uint32_t status = NRF_SUCCESS;
    
    p_params.on_off = pin_state;
    p_params.tid = tid++;

    transition_params.delay_ms = APP_CONFIG_ONOFF_DELAY_MS;
    transition_params.transition_time_ms = APP_CONFIG_ONOFF_TRANSITION_TIME_MS;
    
    
    status = generic_onoff_client_set_unack(&m_client, &p_params, &transition_params, APP_UNACK_MSG_REPEAT_COUNT);

    
    switch (status)
    {
        case NRF_SUCCESS:
            break;

        case NRF_ERROR_NO_MEM:
        case NRF_ERROR_BUSY:
        case NRF_ERROR_INVALID_STATE:
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client cannot send\n");
            // hal_led_blink_ms(LEDS_MASK, LED_BLINK_SHORT_INTERVAL_MS, LED_BLINK_CNT_NO_REPLY);
            break;

        case NRF_ERROR_INVALID_PARAM:
            /* Publication not enabled for this client. One (or more) of the following is wrong:
             * - An application key is missing, or there is no application key bound to the model
             * - The client does not have its publication state set
             *
             * It is the provisioner that adds an application key, binds it to the model and sets
             * the model's publication state.
             */
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Publication not configured for client\n");
            break;

        default:
            ERROR_CHECK(status);
            break;
    }
}

static void gpiote_init()
{
    pin_number = PIN_NUMBER;
    pin_state = P_STARTING_STATE;

    if(P_STARTING_STATE == P_INPUT){
        gpio_init_input();
    } else {
        gpio_init_output();
    }

}

static void gpio_init_input()
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Init gpio as input\n");
    nrfx_gpiote_out_uninit(PIN_NUMBER);
    nrfx_gpiote_in_config_t in_config = NRFX_GPIOTE_CONFIG_IN_SENSE_TOGGLE(true);
    in_config.pull = NRF_GPIO_PIN_PULLDOWN;
    ERROR_CHECK(nrfx_gpiote_in_init(PIN_NUMBER, &in_config, in_pin_handler));
    nrfx_gpiote_in_event_enable(PIN_NUMBER, true);
}

static void gpio_init_output()
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Init gpio as output\n");
    nrfx_gpiote_in_uninit(PIN_NUMBER);
    nrfx_gpiote_out_config_t out_config = NRFX_GPIOTE_CONFIG_OUT_SIMPLE(true); // << TODO WHAT IS THIS TRUE
    ERROR_CHECK(nrfx_gpiote_out_init(PIN_NUMBER, &out_config));
}

/* COMMON STUFF */

static void node_reset(void)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "----- Node reset  -----\n");
    // hal_led_blink_ms(LEDS_MASK, LED_BLINK_INTERVAL_MS, LED_BLINK_CNT_RESET); // TODO DELETE HAL
    /* This function may return if there are ongoing flash operations. */
    mesh_stack_device_reset();
}

static void config_server_evt_cb(const config_server_evt_t * p_evt)
{
    if (p_evt->type == CONFIG_SERVER_EVT_NODE_RESET)
    {
        node_reset();
    }
}

static void mesh_init(void)
{
    mesh_stack_init_params_t init_params =
    {
        .core.irq_priority       = NRF_MESH_IRQ_PRIORITY_LOWEST,
        .core.lfclksrc           = DEV_BOARD_LF_CLK_CFG,
        .core.p_uuid             = NULL,
        .models.models_init_cb   = models_init_cb,
        .models.config_server_cb = config_server_evt_cb
    };
    ERROR_CHECK(mesh_stack_init(&init_params, &m_device_provisioned));
}


// TODO DELETE HAL
/*
static void button_event_handler(uint32_t button_number)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Button %u pressed\n", button_number);
    switch(button_number)
    {
        case 0:
            if(mesh_stack_is_device_provisioned()){
                __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Resetting node.\n");
#if MESH_FEATURE_GATT_PROXY_ENABLED
                (void) proxy_stop();
#endif
                mesh_stack_config_clear();
                node_reset();
            } else {
                __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "The device is unprovisioned. Resetting has no effect.\n");   
            }
            break;
        default:
        break;
    }
}
*/


static void initialise(void)
{
    __LOG_INIT(LOG_SRC_APP | LOG_SRC_ACCESS | LOG_SRC_BEARER, LOG_LEVEL_INFO, LOG_CALLBACK_DEFAULT);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "----- ex08 Universal with a simple onoff server to switch pin input/output -----\n");

    ERROR_CHECK(nrfx_gpiote_init());
    gpiote_init();

    ERROR_CHECK(app_timer_init());
    // hal_leds_init(); // TODO DELETE HAL

    // ERROR_CHECK(hal_buttons_init(button_event_handler)); // TODO DELETE HAL

    ble_stack_init();

#if MESH_FEATURE_GATT_ENABLED
    gap_params_init();
    conn_params_init();
#endif

    mesh_init();

}

/*************************************************************************************************/

int main(void)
{
    initialise();
    start();

    for (;;)
    {
        (void)sd_app_evt_wait();
    }
}