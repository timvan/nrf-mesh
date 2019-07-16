/* TODO */
/* 
CHECK HOW LEDS AFFECT THE PINS - should we remove the hal and leds


 */
/***************/

#include <stdint.h>
#include <string.h>
#include <stdlib.h> 

/* HAL */
#include "boards.h"
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
#include "simple_on_off_server.1.h"

/* Logging and RTT */
#include "log.h"
#include "rtt_input.h"

/* Example specific includes */
#include "app_config.h"
#include "example_common.h"
#include "nrf_mesh_config_examples.h"
#include "light_switch_example_common.h"
#include "app_onoff.1.h"
#include "ble_softdevice_support.h"

#include "nrfx_gpiote.h"

#define N_ELEMS(x) (sizeof(x) / sizeof(x[0]))

#define APP_STARTING_INDEX     (1)

#define APP_STATE_OFF                (0)
#define APP_STATE_ON                 (1)
#define APP_UNACK_MSG_REPEAT_COUNT   (2)

#define PINS {12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25}
// #define PINS_STARTING_STATE [12, 13, 14, 15, 16, 17, 18, 19, 20, 22, 23, 24, 25];

#define UNPROVISION_PIN 11
#define P_INPUT true
#define P_OUTPUT false
#define P_STARTING_STATE P_OUTPUT

// #define NEW_TIMER(_name, timer_id) APP_TIMER_DEF( _name ## timer_id ## _timer);

// TODO sort this temp
#define TEMP_PIN 12

static bool m_device_provisioned;

// OLD START
// APP_TIMER_DEF(m_onoff_server_0_timer);
// static app_onoff_server_t m_onoff_server_0;

// static generic_onoff_client_t m_client; 

// static simple_on_off_server_t m_simple_on_off_server;

static bool pin_state;
// static int pin_number;
// OLD END

typedef enum {Output, Input} io;

typedef struct
{
    app_onoff_server_t m_onoff_server;
    generic_onoff_client_t m_client;
    simple_on_off_server_t m_simple_on_off_server;
    uint8_t pin_number;
    io pin_purpose;
} universal_app;

static uint8_t gpio_pins[] = PINS;
static universal_app u_apps[N_ELEMS(gpio_pins)];
int temp = TEMP_PIN;

APP_TIMER_DEF(m_onoff_server_12_timer);
APP_TIMER_DEF(m_onoff_server_13_timer);
APP_TIMER_DEF(m_onoff_server_14_timer);
APP_TIMER_DEF(m_onoff_server_15_timer);
APP_TIMER_DEF(m_onoff_server_16_timer);
APP_TIMER_DEF(m_onoff_server_17_timer);
APP_TIMER_DEF(m_onoff_server_18_timer);
APP_TIMER_DEF(m_onoff_server_19_timer);
APP_TIMER_DEF(m_onoff_server_20_timer);
APP_TIMER_DEF(m_onoff_server_22_timer);
APP_TIMER_DEF(m_onoff_server_23_timer);
APP_TIMER_DEF(m_onoff_server_24_timer);
APP_TIMER_DEF(m_onoff_server_25_timer);

const app_timer_id_t* timers[] = {&m_onoff_server_12_timer, &m_onoff_server_13_timer, &m_onoff_server_14_timer, &m_onoff_server_15_timer, &m_onoff_server_16_timer, &m_onoff_server_17_timer, &m_onoff_server_18_timer, &m_onoff_server_19_timer, &m_onoff_server_20_timer, &m_onoff_server_22_timer, &m_onoff_server_23_timer, &m_onoff_server_24_timer, &m_onoff_server_25_timer};

// fwd declerartions
static void initialise(void);
static void gpiote_init(void);
static void gpio_init_input(uint8_t pin_number);
static void gpio_init_output(uint8_t pin_number);
static void gpiote_input_handler(nrfx_gpiote_pin_t pin, nrf_gpiote_polarity_t action);
static void unprovision_gpio_init(void);

static void mesh_init(void);
static void models_init_cb(void);

// server cbs (pin is output)
static void app_onoff_server_set_cb(const app_onoff_server_t * p_server, bool onoff);
static void app_onoff_server_get_cb(const app_onoff_server_t * p_server, bool * p_present_onoff);

// client cbs (pin is input)
static void app_gen_onoff_client_publish_interval_cb(access_model_handle_t handle, void * p_self);
static void app_generic_onoff_client_status_cb(const generic_onoff_client_t * p_self, const access_message_rx_meta_t * p_meta, const generic_onoff_status_params_t * p_in);
static void app_gen_onoff_client_transaction_status_cb(access_model_handle_t model_handle, void * p_args, access_reliable_status_t status);
const generic_onoff_client_callbacks_t client_cbs = {
    .onoff_status_cb = app_generic_onoff_client_status_cb,
    .ack_transaction_status_cb = app_gen_onoff_client_transaction_status_cb,
    .periodic_publish_cb = app_gen_onoff_client_publish_interval_cb
};
// simple server cbs (changes pin config)
static bool app_simple_onoff_server_get_cb(const simple_on_off_server_t * p_self);
static bool app_simple_onoff_server_set_cb(const simple_on_off_server_t * p_self, bool on);

static void config_server_evt_cb(const config_server_evt_t * p_evt);
static void node_reset(void);

static void start(void);

static void provision(void);
static void provisioning_complete_cb(void);
static void device_identification_start_cb(uint8_t attention_duration_s);
static void provisioning_aborted_cb(void);
static void unprovision(void);

static void rtt_input_handler(int key);
int pin_to_index(uint8_t pin_number);
  
int main(void)
{
    initialise();
    start();

    for (;;)
    {
        (void)sd_app_evt_wait();
    }
}

static void initialise(void)
{
    __LOG_INIT(LOG_SRC_APP | LOG_SRC_ACCESS | LOG_SRC_BEARER, LOG_LEVEL_INFO, LOG_CALLBACK_DEFAULT);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "\n\n");
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "----------------------------------------------------------------------------------- -\n");
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "----- ex09 Multi Universal - GClients, GServers and Simple Server for each pin -----\n");
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "------------------------------------------------------------------------------------\n");


    ERROR_CHECK(nrfx_gpiote_init());
    gpiote_init();

    ERROR_CHECK(app_timer_init());

    ble_stack_init();

#if MESH_FEATURE_GATT_ENABLED
    gap_params_init();
    conn_params_init();
#endif

    mesh_init();

}

/***************************************************/
/* GPIOTE INIT                                     */
/***************************************************/

static void gpiote_init(void)
{
    int i;
    uint8_t pin_number;
    for(i = 0; i < N_ELEMS(gpio_pins); i++)
    {
        pin_number = gpio_pins[i];
        gpio_init_output(pin_number);
    }
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "gpiote_init - %d elements\n", i);

    unprovision_gpio_init();
}

static void gpio_init_input(uint8_t pin_number)
{
//    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Init gpio %d as input\n", pin_number);
    nrfx_gpiote_out_uninit(pin_number);
    nrfx_gpiote_in_config_t in_config = NRFX_GPIOTE_CONFIG_IN_SENSE_TOGGLE(true); // TODO - this should be configurable - i.e set up/down/toggle
    in_config.pull = NRF_GPIO_PIN_PULLUP;
    ERROR_CHECK(nrfx_gpiote_in_init(pin_number, &in_config, gpiote_input_handler));
    nrfx_gpiote_in_event_enable(pin_number, true);
}

static void gpio_init_output(uint8_t pin_number)
{
//    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Init gpio %d as output\n", pin_number);
    nrfx_gpiote_in_uninit(pin_number);
    nrfx_gpiote_out_config_t out_config = NRFX_GPIOTE_CONFIG_OUT_SIMPLE(false); // << TODO WHAT IS THIS TRUE
    ERROR_CHECK(nrfx_gpiote_out_init(pin_number, &out_config));
}

static void unprovision_handler(nrfx_gpiote_pin_t pin, nrf_gpiote_polarity_t action)
{
    unprovision();
}

static void unprovision_gpio_init(void)
{
  int pin_number = UNPROVISION_PIN;
  
  __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Init gpio %d as unprovision pin (input)\n", pin_number);
  nrfx_gpiote_out_uninit(pin_number);
  nrfx_gpiote_in_config_t in_config = NRFX_GPIOTE_CONFIG_IN_SENSE_TOGGLE(true);
  in_config.pull = NRF_GPIO_PIN_PULLUP;
  ERROR_CHECK(nrfx_gpiote_in_init(pin_number, &in_config, unprovision_handler));
  nrfx_gpiote_in_event_enable(pin_number, true);

}

/***************************************************/
/* INPUT HANDLER                                   */
/***************************  ************************/

static void gpiote_input_handler(nrfx_gpiote_pin_t pin, nrf_gpiote_polarity_t action)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client - SEND GPIO %d is [%d]\n", pin, nrf_gpio_pin_read(pin));
    uint8_t element_index = pin_to_index(pin);

    generic_onoff_client_t *m_client = &(u_apps[element_index].m_client);

    generic_onoff_set_params_t set_params;
    model_transition_t transition_params;
    static uint8_t tid = 0;
    uint32_t status = NRF_SUCCESS;
    
    set_params.on_off = nrf_gpio_pin_read(pin);
    set_params.tid = tid++;

    transition_params.delay_ms = APP_CONFIG_ONOFF_DELAY_MS;
    transition_params.transition_time_ms = APP_CONFIG_ONOFF_TRANSITION_TIME_MS;
    
    // TODO - this is only unack atm
    status = generic_onoff_client_set_unack(m_client, &set_params, &transition_params, APP_UNACK_MSG_REPEAT_COUNT);

    switch (status)
    {
        case NRF_SUCCESS:
            break;

        case NRF_ERROR_NO_MEM:
        case NRF_ERROR_BUSY:
        case NRF_ERROR_INVALID_STATE:
            __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client cannot send\n");
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

/***************************************************/
/* MESH INIT                                       */
/***************************************************/

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

/***************************************************/
/* MODEL CALLBACKS                                 */
/***************************************************/

static void models_init_cb(void)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Initializing and adding models\n");

    uint8_t pin_number;

    for(int i = 0; i < N_ELEMS(gpio_pins); i++)
    {
        pin_number = gpio_pins[i];

        u_apps[i].pin_number = pin_number;

        /* init server */

        u_apps[i].m_onoff_server.server.settings.force_segmented = APP_CONFIG_FORCE_SEGMENTATION;
        u_apps[i].m_onoff_server.server.settings.transmic_size = APP_CONFIG_MIC_SIZE;
        u_apps[i].m_onoff_server.p_timer_id = timers[i];
        u_apps[i].m_onoff_server.onoff_set_cb = app_onoff_server_set_cb;
        u_apps[i].m_onoff_server.onoff_get_cb = app_onoff_server_get_cb;
        u_apps[i].m_onoff_server.pin_number = pin_number;

        ERROR_CHECK(app_onoff_init(&u_apps[i].m_onoff_server, APP_STARTING_INDEX + i));


        /* init client */

        u_apps[i].m_client.settings.p_callbacks = &client_cbs;
        u_apps[i].m_client.settings.timeout = 0;
        u_apps[i].m_client.settings.force_segmented = APP_CONFIG_FORCE_SEGMENTATION;
        u_apps[i].m_client.settings.transmic_size = APP_CONFIG_MIC_SIZE;
        ERROR_CHECK(generic_onoff_client_init(&u_apps[i].m_client, APP_STARTING_INDEX + i));
        

        /* init config server */

        u_apps[i].m_simple_on_off_server.get_cb = &app_simple_onoff_server_get_cb;
        u_apps[i].m_simple_on_off_server.set_cb = &app_simple_onoff_server_set_cb;
        u_apps[i].m_simple_on_off_server.pin_number = pin_number;
        ERROR_CHECK(simple_on_off_server_init(&u_apps[i].m_simple_on_off_server, APP_STARTING_INDEX + i));
    }
}

/***************************************************/
/* SERVER CALLBACKS (PIN IS OUTPUT)                */
/***************************************************/

static void app_onoff_server_set_cb(const app_onoff_server_t * p_server, bool onoff)
{
    int pin_number = p_server->pin_number;
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Server - SET GPIO %d to [%d]\n", pin_number, onoff);
    if(onoff){
        nrfx_gpiote_out_set(pin_number);
    } else {
        nrfx_gpiote_out_clear(pin_number);
    }
}

static void app_onoff_server_get_cb(const app_onoff_server_t * p_server, bool * p_present_onoff)
{
    int pin_number = p_server->pin_number;
    *p_present_onoff = nrf_gpio_pin_read(pin_number);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Server - GPIO %d is [%d]\n", pin_number, p_present_onoff)
}

/***************************************************/
/* CLIENT CALLBACKS (PIN IS INPUT)                 */
/***************************************************/

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

/***************************************************/
/* SIMPLE SERVER CALLBACKS - CHANGES PIN CONFIG    */
/***************************************************/

static bool app_simple_onoff_server_get_cb(const simple_on_off_server_t * p_self)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Simple server-on-off - get\n");
    return false; // TODO - need to return server state
}

static bool app_simple_onoff_server_set_cb(const simple_on_off_server_t * p_self, bool on)
{

    int pin_number = p_self->pin_number;

    if(on){
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Simple server-on-off - set GPIO %d as P_INPUT \n", pin_number);
    } else {
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Simple server-on-off - set GPIO %d as P_OUTPUT \n", pin_number);
    }
    
    if(on == P_INPUT){
        gpio_init_input(pin_number);
    } else {
        gpio_init_output(pin_number);
    }
    
    return on;
}

/***************************************************/
/* CONFIG SERVER CALLBACKS                         */
/***************************************************/

static void config_server_evt_cb(const config_server_evt_t * p_evt)
{
    if (p_evt->type == CONFIG_SERVER_EVT_NODE_RESET)
    {
        node_reset();
    }
}

static void node_reset(void)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "----- Node reset  -----\n");
    /* This function may return if there are ongoing flash operations. */
    mesh_stack_device_reset();
}

/***************************************************/
/* START                                           */
/***************************************************/

static void start(void)
{
    rtt_input_enable(rtt_input_handler, RTT_INPUT_POLL_PERIOD_MS);

    if (!m_device_provisioned) {
        provision();
    }

    mesh_app_uuid_print(nrf_mesh_configure_device_uuid_get());

    ERROR_CHECK(mesh_stack_start());

}

/***************************************************/
/* PROVISIONING                                    */
/***************************************************/

static void provision(void)
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

static void provisioning_complete_cb(void)
{
    
#if MESH_FEATURE_GATT_ENABLED
    /* Restores the application parameters after switching from the Provisioning
     * service to the Proxy  */
    gap_params_init();
    conn_params_init();
#endif

    dsm_local_unicast_address_t node_address;
    dsm_local_unicast_addresses_get(&node_address);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Node Address: 0x%04x \n", node_address.address_start);
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Successfully provisioned\n");
}

static void device_identification_start_cb(uint8_t attention_duration_s)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Provisioning - start device identification \n");
}

static void provisioning_aborted_cb(void)
{
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Provisioning aborted\n");
}

static void unprovision(void)
{

    if (mesh_stack_is_device_provisioned()) {
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Unprovisioning device\n");
#if MESH_FEATURE_GATT_PROXY_ENABLED
        (void) proxy_stop();
#endif
        mesh_stack_config_clear();
        node_reset();
    } else {
        __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Device is not provisioned\n");
    }
}

/***************************************************/
/* RTT                                             */
/***************************************************/

static void rtt_input_handler(int key)
{
    key = key - '0';
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "rtt %u pressed\n", key);

    if(key == 0){
        unprovision();
    }

//    uint32_t status = NRF_SUCCESS;
//     generic_onoff_set_params_t set_params;
//     model_transition_t transition_params;
//     static uint8_t tid = 0;
//     bool new_state;

//     /* Button 1: On, Button 2: Off, Client[0]
//      * Button 2: On, Button 3: Off, Client[1]
//      */

//     switch(key)
//     {
//         case 0:
//         case 2:
//             set_params.on_off = APP_STATE_ON;
//             break;

//         case 1:
//         case 3:
//             set_params.on_off = APP_STATE_OFF;
//             break;
            
//     }

//     set_params.tid = tid++;
//     transition_params.delay_ms = APP_CONFIG_ONOFF_DELAY_MS;
//     transition_params.transition_time_ms = APP_CONFIG_ONOFF_TRANSITION_TIME_MS;

//     switch (key)
//     {
//         case 0:
//         case 1:
//             /* Demonstrate acknowledged transaction, using 1st client model instance */
//             /* In this examples, users will not be blocked if the model is busy */
//             (void)access_model_reliable_cancel(m_client.model_handle);
//             status = generic_onoff_client_set(&m_client, &set_params, &transition_params);
//             // hal_led_pin_set(BSP_LED_0, set_params.on_off); // TODO DELETE HAL
//             __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Sending msg: ONOFF SET ACK %d\n", set_params.on_off);
//             break;

//         case 2:
//         case 3:
//             /* Demonstrate un-acknowledged transaction, using 2nd client model instance */
//             status = generic_onoff_client_set_unack(&m_client, &set_params,
//                                                     &transition_params, APP_UNACK_MSG_REPEAT_COUNT);
//             // hal_led_pin_set(BSP_LED_1, set_params.on_off); // TODO DELETE HAL
//             __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Sending msg: ONOFF SET %d\n", set_params.on_off);
//             break;
//         case 4:
//             status = generic_onoff_client_get(&m_client);
//             __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Sending msg: ONOFF GET \n");
//             break;
//         case 5:
//             new_state = P_INPUT;
//             if(pin_state == P_INPUT){
//               new_state = P_OUTPUT;
//             }
//             app_simple_onoff_server_set_cb(&m_simple_on_off_server, new_state);
//             __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "swapping gpio state \n");
//             break;
//         case 6:
//             node_reset();
//             break;

//     }

//     switch (status)
//     {
//         case NRF_SUCCESS:
//             break;

//         case NRF_ERROR_NO_MEM:
//         case NRF_ERROR_BUSY:
//         case NRF_ERROR_INVALID_STATE:
//             __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Client cannot send\n");
//             // hal_led_blink_ms(LEDS_MASK, LED_BLINK_SHORT_INTERVAL_MS, LED_BLINK_CNT_NO_REPLY); // TODO DELETE HAL
//             break;

//         case NRF_ERROR_INVALID_PARAM:
//             /* Publication not enabled for this client. One (or more) of the following is wrong:
//              * - An application key is missing, or there is no application key bound to the model
//              * - The client does not have its publication state set
//              *
//              * It is the provisioner that adds an application key, binds it to the model and sets
//              * the model's publication state.
//              */
//             __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Publication not configured for client\n");
//             break;

//         default:
//             ERROR_CHECK(status);
//             break;
//     }
}

int pin_to_index(uint8_t pin_number){
    
    for(int i = 0; i < N_ELEMS(gpio_pins); i++)
    {
        if(pin_number == gpio_pins[i]){
            return i;
        }
    }
    __LOG(LOG_SRC_APP, LOG_LEVEL_INFO, "Error - pin %d not found\n", pin_number);
    exit(EXIT_FAILURE);
}